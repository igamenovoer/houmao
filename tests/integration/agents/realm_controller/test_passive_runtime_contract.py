"""Exercise native headless launch and control through the passive API."""

from __future__ import annotations

import json
from pathlib import Path
from time import monotonic, sleep
from typing import Any

from fastapi.testclient import TestClient

from houmao.agents.realm_controller.manifest import load_session_manifest
from houmao.agents.realm_controller.registry_storage import load_managed_agent_record_by_agent_id
from houmao.execution.tmux import TmuxServer
from houmao.passive_server.app import create_app
from houmao.passive_server.config import PassiveServerConfig
from houmao.passive_server.models import (
    PassiveAgentActionResponse,
    PassiveHeadlessLaunchRequest,
    PassiveHeadlessLaunchResponse,
    PassiveHeadlessTurnAcceptedResponse,
    PassiveHeadlessTurnStatusResponse,
)
from houmao.server.models import HoumaoManagedAgentStateResponse
from tests.integration.agents.realm_controller.test_registry_runtime_contract import (
    isolated_startup as isolated_startup,
)


def test_passive_api_launch_control_and_stop_on_the_selected_tmux_server(
    isolated_startup: tuple[TmuxServer, dict[str, Any]],
) -> None:
    """Run one synthetic Claude turn through an actual managed launch and stop."""

    server, runtime = isolated_startup
    owner_root = runtime["runtime_root"].parent
    native_cli = owner_root / "bin" / "claude"
    provider_result = {
        "type": "result",
        "subtype": "success",
        "session_id": "b75a8e5c-bece-4904-b918-6545f648c50d",
        "result": "fixture answer",
    }
    stdout = json.dumps(provider_result) + "\n"
    native_cli.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = --version ]; then printf '2.1.3 (Claude Code)\\n'; exit 0; fi\n"
        'for arg in "$@"; do\n'
        '  if [ "$arg" = "fixture prompt" ]; then\n'
        f"    printf '%s\\n' '{stdout.rstrip()}'\n"
        "    printf 'fixture diagnostics\\n' >&2\n"
        "    exit 0\n"
        "  fi\n"
        "done\n"
        "exit 42\n",
        encoding="utf-8",
    )
    config = PassiveServerConfig(
        api_base_url="http://127.0.0.1:19891",
        runtime_root=runtime["runtime_root"],
        registry_root=owner_root / "registry",
    )
    launch_request = PassiveHeadlessLaunchRequest(
        tool="claude",
        working_directory=str(runtime["working_directory"]),
        agent_def_dir=str(runtime["agent_def_dir"]),
        brain_manifest_path=str(runtime["brain_manifest_path"]),
        role_name=runtime["role_name"],
        agent_name=runtime["agent_name"],
        agent_id=runtime["agent_id"],
    )

    with TestClient(create_app(config=config), base_url=config.api_base_url) as client:
        launch = client.post(
            "/houmao/agents/headless/launches", json=launch_request.model_dump(mode="json")
        )
        assert launch.status_code == 200, launch.text
        receipt = PassiveHeadlessLaunchResponse.model_validate(launch.json())
        manifest = load_session_manifest(Path(receipt.manifest_path)).payload
        assert manifest["registry_launch_authority"] == "external"
        assert manifest["tmux"]["socket_path"] == server.socket_path
        assert server.list_sessions() == {"sentinel", manifest["tmux"]["session_name"]}
        registry = load_managed_agent_record_by_agent_id(runtime["agent_id"])
        assert registry is not None
        assert registry.runtime.manifest_path == receipt.manifest_path
        assert registry.generation_id == manifest["registry_generation_id"]

        selected = f"/houmao/agents/{receipt.tracked_agent_id}"
        state = client.get(f"{selected}/managed-state")
        assert state.status_code == 200, state.text
        managed_state = HoumaoManagedAgentStateResponse.model_validate(state.json())
        assert managed_state.identity.agent_id == runtime["agent_id"]
        assert managed_state.identity.transport == "headless"

        submitted = client.post(f"{selected}/turns", json={"prompt": "fixture prompt"})
        assert submitted.status_code == 200, submitted.text
        accepted = PassiveHeadlessTurnAcceptedResponse.model_validate(submitted.json())
        turn_url = f"{selected}/turns/{accepted.turn_id}"
        deadline = monotonic() + 12.0
        while True:
            polled = client.get(turn_url)
            assert polled.status_code == 200, polled.text
            status = PassiveHeadlessTurnStatusResponse.model_validate(polled.json())
            if status.status != "active":
                break
            assert monotonic() < deadline, "Synthetic headless turn did not settle"
            sleep(0.05)
        assert status.status == "completed", status
        assert client.get(f"{turn_url}/artifacts/stdout").text == stdout
        assert client.get(f"{turn_url}/artifacts/stderr").text == "fixture diagnostics\n"

        stopped = client.post(f"{selected}/stop")
        assert stopped.status_code == 200, stopped.text
        assert PassiveAgentActionResponse.model_validate(stopped.json()).status == "ok"
        assert server.list_sessions() == {"sentinel"}
        assert load_managed_agent_record_by_agent_id(runtime["agent_id"]) is None
