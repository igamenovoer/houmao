from __future__ import annotations

import io
import json
import os
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from urllib import error

import pytest

from houmao.agents.realm_controller.backends import cao_rest as cao_rest_backend
from houmao.agents.realm_controller.agent_identity import (
    AGENT_DEF_DIR_ENV_VAR,
    AGENT_MANIFEST_PATH_ENV_VAR,
    derive_agent_id_from_name,
)
from houmao.agents.realm_controller.backends.cao_rest import (
    CaoRestSession,
    CaoSessionState,
    _compose_tmux_launch_env,
    _ensure_required_executable,
    generate_cao_session_name,
    install_cao_profile,
    render_cao_profile,
)
from houmao.agents.realm_controller.errors import (
    BackendExecutionError,
)
from houmao.agents.realm_controller.mail_commands import (
    parse_mail_result,
    prepare_mail_prompt,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
)
from houmao.agents.mailbox_runtime_models import MailboxResolvedConfig
from houmao.agents.mailbox_runtime_support import mailbox_env_bindings
from houmao.agents.realm_controller.backends.shadow_parser_core import (
    ANOMALY_STALLED_ENTERED,
    ANOMALY_STALLED_RECOVERED,
)
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.cao.models import (
    CaoHealthResponse,
    CaoSessionDetail,
    CaoSessionInfo,
    CaoSessionTerminalSummary,
    CaoSuccessResponse,
    CaoTerminal,
    CaoTerminalOutputResponse,
    CaoTerminalStatus,
)
from houmao.cao.rest_client import CaoApiError, CaoRestClient


class _FakeResponse:
    def __init__(self, status: int, payload: object) -> None:
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_cao_preflight_reports_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.shutil.which",
        lambda _: None,
    )
    with pytest.raises(BackendExecutionError, match="command -v cao-server"):
        _ensure_required_executable(
            executable="cao-server",
            flow="CAO-backed runtime flow",
        )


def test_cao_preflight_accepts_present_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.shutil.which",
        lambda _: "/usr/bin/cao-server",
    )
    _ensure_required_executable(
        executable="cao-server",
        flow="CAO-backed runtime flow",
    )


def _sample_launch_plan(tmp_path: Path, *, tool: str = "codex") -> LaunchPlan:
    env_file = tmp_path / f"{tool}-vars.env"
    if tool == "codex":
        env_file.write_text(
            "OPENAI_API_KEY=from-profile\nUNALLOWLISTED_TMUX_VAR=present\n",
            encoding="utf-8",
        )
    else:
        env_file.write_text(
            "ANTHROPIC_API_KEY=from-profile\nUNALLOWLISTED_TMUX_VAR=present\n",
            encoding="utf-8",
        )

    return LaunchPlan(
        backend="cao_rest",
        tool=tool,
        executable=tool,
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME" if tool == "codex" else "CLAUDE_CONFIG_DIR",
        home_path=tmp_path / "home",
        env={"OPENAI_API_KEY": "secret"} if tool == "codex" else {"ANTHROPIC_API_KEY": "secret"},
        env_var_names=["OPENAI_API_KEY"] if tool == "codex" else ["ANTHROPIC_API_KEY"],
        role_injection=RoleInjectionPlan(
            method="cao_profile",
            role_name="gpu-kernel-coder",
            prompt="Be precise",
        ),
        metadata={"env_source_file": str(env_file)},
    )


def _sample_mailbox_launch_plan(tmp_path: Path, *, tool: str = "codex") -> LaunchPlan:
    plan = _sample_launch_plan(tmp_path, tool=tool)
    mailbox_root = tmp_path / "mailbox"
    principal_id = "AGENTSYS-research"
    address = "AGENTSYS-research@agents.localhost"
    bootstrap_filesystem_mailbox(
        mailbox_root,
        principal=MailboxPrincipal(principal_id=principal_id, address=address),
    )
    mailbox = MailboxResolvedConfig(
        transport="filesystem",
        principal_id=principal_id,
        address=address,
        filesystem_root=mailbox_root.resolve(),
        bindings_version="2026-03-12T05:00:00.000001Z",
    )
    bindings = mailbox_env_bindings(mailbox)
    return replace(
        plan,
        env={**plan.env, **bindings},
        env_var_names=sorted({*plan.env_var_names, *bindings.keys()}),
        mailbox=mailbox,
    )


def _sample_shadow_policy_launch_plan(
    tmp_path: Path,
    *,
    unknown_timeout_seconds: float,
    completion_stability_seconds: float = 1.0,
    stalled_is_terminal: bool,
) -> LaunchPlan:
    plan = _sample_launch_plan(tmp_path, tool="codex")
    plan.metadata["cao_shadow_policy_config"] = {
        "unknown_to_stalled_timeout_seconds": unknown_timeout_seconds,
        "completion_stability_seconds": completion_stability_seconds,
        "stalled_is_terminal": stalled_is_terminal,
    }
    return plan


def _install_fake_clock(monkeypatch: pytest.MonkeyPatch, *, tick_seconds: float) -> None:
    clock = {"now": 0.0}

    def _fake_monotonic() -> float:
        return float(clock["now"])

    def _fake_sleep(seconds: float) -> None:
        del seconds
        clock["now"] = float(clock["now"]) + tick_seconds

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.time.monotonic",
        _fake_monotonic,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.time.sleep",
        _fake_sleep,
    )


def test_compose_tmux_launch_env_preserves_claude_model_vars_from_caller_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ANTHROPIC_MODEL", "opus")
    monkeypatch.setenv("ANTHROPIC_SMALL_FAST_MODEL", "claude-3-5-haiku-latest")
    monkeypatch.setenv("CLAUDE_CODE_SUBAGENT_MODEL", "sonnet")

    launch_env = _compose_tmux_launch_env(_sample_launch_plan(tmp_path, tool="claude"))

    assert launch_env["ANTHROPIC_MODEL"] == "opus"
    assert launch_env["ANTHROPIC_SMALL_FAST_MODEL"] == "claude-3-5-haiku-latest"
    assert launch_env["CLAUDE_CODE_SUBAGENT_MODEL"] == "sonnet"


def test_compose_tmux_launch_env_injects_loopback_no_proxy_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)

    launch_env = _compose_tmux_launch_env(
        _sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9991",
    )

    assert launch_env["HTTP_PROXY"] == "http://proxy.internal:8080"
    no_proxy_tokens = launch_env["NO_PROXY"].split(",")
    assert "corp.internal" in no_proxy_tokens
    assert "localhost" in no_proxy_tokens
    assert "127.0.0.1" in no_proxy_tokens
    assert "::1" in no_proxy_tokens
    assert launch_env["no_proxy"] == launch_env["NO_PROXY"]


def test_compose_tmux_launch_env_preserve_mode_leaves_no_proxy_untouched(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("AGENTSYS_PRESERVE_NO_PROXY_ENV", "1")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)

    launch_env = _compose_tmux_launch_env(
        _sample_launch_plan(tmp_path),
        api_base_url="http://localhost:9991",
    )

    assert launch_env["HTTP_PROXY"] == "http://proxy.internal:8080"
    assert launch_env["NO_PROXY"] == "corp.internal"
    assert "no_proxy" not in launch_env


def test_compose_tmux_launch_env_non_loopback_keeps_no_proxy_unchanged(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)

    launch_env = _compose_tmux_launch_env(
        _sample_launch_plan(tmp_path),
        api_base_url="http://cao.internal:9889",
    )

    assert launch_env["NO_PROXY"] == "corp.internal"
    assert "no_proxy" not in launch_env


def test_cao_rest_client_request_shapes(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, str, bytes | None]] = []

    def _fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        captured.append((req.get_method(), req.full_url, req.data))
        payload: object = {"success": True}
        if req.full_url.endswith("/health"):
            payload = {"status": "ok", "service": "cli-agent-orchestrator"}
        if req.full_url.endswith("/sessions/s1"):
            payload = {
                "session": {"id": "s1", "name": "s1", "status": "attached"},
                "terminals": [
                    {
                        "id": "a1b2c3d4",
                        "tmux_session": "s1",
                        "tmux_window": "developer-1",
                        "provider": "codex",
                        "agent_profile": "role_profile",
                        "last_active": None,
                    }
                ],
            }
        if "/sessions/s1/terminals" in req.full_url:
            payload = {
                "id": "a1b2c3d4",
                "name": "developer-1",
                "provider": "codex",
                "session_name": "s1",
                "agent_profile": "role_profile",
                "status": "idle",
            }
        if "/terminals/a1b2c3d4/output" in req.full_url:
            payload = {"output": "hello", "mode": "last"}
        if req.full_url.endswith("/terminals/a1b2c3d4"):
            payload = {
                "id": "a1b2c3d4",
                "name": "developer-1",
                "provider": "codex",
                "session_name": "s1",
                "agent_profile": "role_profile",
                "status": "idle",
            }
        return _FakeResponse(status=200, payload=payload)

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    client = CaoRestClient("http://127.0.0.1:9991")
    health = client.health()
    session_detail = client.get_session_detail("s1")
    terminal = client.create_terminal(
        "s1",
        provider="codex",
        agent_profile="role_profile",
        working_directory="/tmp/work",
    )
    sent = client.send_terminal_input("a1b2c3d4", "hello")
    output = client.get_terminal_output("a1b2c3d4", mode="last")
    fetched = client.get_terminal("a1b2c3d4")

    assert health == CaoHealthResponse(status="ok", service="cli-agent-orchestrator")
    assert session_detail == CaoSessionDetail(
        session=CaoSessionInfo(id="s1", name="s1", status="attached"),
        terminals=[
            CaoSessionTerminalSummary(
                id="a1b2c3d4",
                tmux_session="s1",
                tmux_window="developer-1",
                provider="codex",
                agent_profile="role_profile",
                last_active=None,
            )
        ],
    )
    assert terminal.provider == "codex"
    assert sent == CaoSuccessResponse(success=True)
    assert output == CaoTerminalOutputResponse(output="hello", mode="last")
    assert fetched.status == CaoTerminalStatus.IDLE

    methods = [item[0] for item in captured]
    urls = [item[1] for item in captured]
    payloads = [item[2] for item in captured]

    assert methods == ["GET", "GET", "POST", "POST", "GET", "GET"]
    assert urls[0].endswith("/health")
    assert urls[1].endswith("/sessions/s1")
    assert (
        urls[2]
        == "http://127.0.0.1:9991/sessions/s1/terminals?provider=codex&agent_profile=role_profile&working_directory=%2Ftmp%2Fwork"
    )
    assert urls[3].endswith("/terminals/a1b2c3d4/input?message=hello")
    assert urls[4].endswith("/terminals/a1b2c3d4/output?mode=last")
    assert urls[5].endswith("/terminals/a1b2c3d4")
    assert payloads == [None, None, None, None, None, None]


def test_cao_rest_client_injects_loopback_no_proxy_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)

    captured: dict[str, str | None] = {}

    def _fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        del req, timeout
        captured["NO_PROXY"] = os.environ.get("NO_PROXY")
        captured["no_proxy"] = os.environ.get("no_proxy")
        return _FakeResponse(
            status=200,
            payload={"status": "ok", "service": "cli-agent-orchestrator"},
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    client = CaoRestClient("http://127.0.0.1:9991")
    health = client.health()

    assert health.status == "ok"
    assert captured["NO_PROXY"] is not None
    assert "corp.internal" in captured["NO_PROXY"].split(",")
    assert "localhost" in captured["NO_PROXY"].split(",")
    assert "127.0.0.1" in captured["NO_PROXY"].split(",")
    assert "::1" in captured["NO_PROXY"].split(",")
    assert captured["no_proxy"] == captured["NO_PROXY"]
    assert os.environ.get("NO_PROXY") == "corp.internal"
    assert os.environ.get("no_proxy") is None


def test_cao_rest_client_parses_unknown_provider_id(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        del timeout
        if req.full_url.endswith("/terminals/term-1"):
            return _FakeResponse(
                status=200,
                payload={
                    "id": "term-1",
                    "name": "developer-1",
                    "provider": "kimi_cli",
                    "session_name": "s1",
                    "agent_profile": "role_profile",
                    "status": "idle",
                },
            )
        raise AssertionError(f"Unexpected URL: {req.full_url}")

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    client = CaoRestClient("http://127.0.0.1:9991")
    terminal = client.get_terminal("term-1")

    assert terminal.provider == "kimi_cli"
    assert terminal.status == CaoTerminalStatus.IDLE


def test_parsed_unknown_provider_does_not_enable_runtime_launch_support(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def _fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        del timeout
        if req.full_url.endswith("/terminals/term-1"):
            return _FakeResponse(
                status=200,
                payload={
                    "id": "term-1",
                    "name": "developer-1",
                    "provider": "kimi_cli",
                    "session_name": "s1",
                    "agent_profile": "role_profile",
                    "status": "idle",
                },
            )
        raise AssertionError(f"Unexpected URL: {req.full_url}")

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    client = CaoRestClient("http://127.0.0.1:9991")
    terminal = client.get_terminal("term-1")

    assert terminal.provider == "kimi_cli"

    with pytest.raises(BackendExecutionError, match="Unsupported CAO provider mapping"):
        CaoRestSession(
            launch_plan=_sample_launch_plan(tmp_path, tool="kimi"),
            api_base_url="http://localhost:9889",
            role_name="gpu-kernel-coder",
            role_prompt="role prompt",
            parsing_mode="cao_only",
        )


def test_cao_rest_client_preserve_mode_leaves_no_proxy_untouched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("AGENTSYS_PRESERVE_NO_PROXY_ENV", "1")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)

    captured: dict[str, str | None] = {}

    def _fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        del req, timeout
        captured["NO_PROXY"] = os.environ.get("NO_PROXY")
        captured["no_proxy"] = os.environ.get("no_proxy")
        return _FakeResponse(
            status=200,
            payload={"status": "ok", "service": "cli-agent-orchestrator"},
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    client = CaoRestClient("http://localhost:9889")
    health = client.health()

    assert health.status == "ok"
    assert captured["NO_PROXY"] == "corp.internal"
    assert captured["no_proxy"] is None
    assert os.environ.get("NO_PROXY") == "corp.internal"
    assert os.environ.get("no_proxy") is None


def test_cao_rest_client_non_loopback_keeps_no_proxy_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.internal:8080")
    monkeypatch.setenv("NO_PROXY", "corp.internal")
    monkeypatch.delenv("no_proxy", raising=False)

    captured: dict[str, str | None] = {}

    def _fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        del req, timeout
        captured["NO_PROXY"] = os.environ.get("NO_PROXY")
        captured["no_proxy"] = os.environ.get("no_proxy")
        return _FakeResponse(
            status=200,
            payload={"status": "ok", "service": "cli-agent-orchestrator"},
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    client = CaoRestClient("http://cao.internal:9889")
    health = client.health()

    assert health.status == "ok"
    assert captured["NO_PROXY"] == "corp.internal"
    assert captured["no_proxy"] is None
    assert os.environ.get("NO_PROXY") == "corp.internal"
    assert os.environ.get("no_proxy") is None


def test_cao_rest_client_http_error_exposes_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_urlopen_error(req, timeout=0):  # type: ignore[no-untyped-def]
        raise error.HTTPError(
            url=req.full_url,
            code=500,
            msg="boom",
            hdrs=None,
            fp=io.BytesIO(b'{"detail":"boom detail"}'),
        )

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen_error)

    client = CaoRestClient("http://localhost:9889")
    with pytest.raises(CaoApiError) as exc_info:
        client.health()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "boom detail"


def test_cao_rest_client_validation_error_has_field_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        return _FakeResponse(status=200, payload={"id": "a1b2c3d4"})

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)

    client = CaoRestClient("http://localhost:9889")
    with pytest.raises(CaoApiError, match=r"\$\.name"):
        client.get_terminal("a1b2c3d4")


def test_render_and_install_cao_profile(tmp_path: Path) -> None:
    name, markdown = render_cao_profile(
        role_name="gpu-kernel-coder",
        role_prompt="You are role text with {{TOKEN}}.",
        prepend="PRE",
        append="POST",
        substitutions={"{{TOKEN}}": "abc"},
    )

    assert name.startswith("gpu-kernel-coder_")
    assert "description:" in markdown
    assert "PRE" in markdown
    assert "POST" in markdown
    assert "abc" in markdown

    path = install_cao_profile(
        profile_name=name,
        markdown=markdown,
        agent_store_dir=tmp_path / "store",
    )
    assert path.is_file()
    assert path.name == f"{name}.md"


def test_cao_backend_rejects_unsupported_tool(tmp_path: Path) -> None:
    with pytest.raises(BackendExecutionError, match="Unsupported CAO provider mapping"):
        CaoRestSession(
            launch_plan=_sample_launch_plan(tmp_path, tool="gemini"),
            api_base_url="http://localhost:9889",
            role_name="gpu-kernel-coder",
            role_prompt="role prompt",
            parsing_mode="cao_only",
        )


def test_cao_backend_rejects_shadow_only_without_runtime_shadow_parser_support(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setitem(cao_rest_backend._CAO_PROVIDER_BY_TOOL, "gemini", "gemini_cli")

    with pytest.raises(BackendExecutionError, match="no runtime shadow parser is available"):
        CaoRestSession(
            launch_plan=_sample_launch_plan(tmp_path, tool="gemini"),
            api_base_url="http://localhost:9889",
            role_name="gpu-kernel-coder",
            role_prompt="role prompt",
            parsing_mode="shadow_only",
        )


@pytest.mark.parametrize("parsing_mode", ["cao_only", "shadow_only"])
def test_cao_backend_uses_tmux_env_and_query_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    parsing_mode: str,
) -> None:
    captured_tmux: dict[str, object] = {}
    captured_create_terminal: dict[str, object] = {}
    captured_codex_bootstrap: dict[str, object] = {}
    selected_window_ids: list[str] = []
    killed_window_ids: list[str] = []
    list_window_calls = {"count": 0}
    monkeypatch.setenv("INHERITED_CALLER_ENV", "caller-value")
    monkeypatch.setenv("OPENAI_API_KEY", "caller-secret")

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self._full_output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            captured_create_terminal["session_name"] = session_name
            captured_create_terminal["provider"] = provider
            captured_create_terminal["agent_profile"] = agent_profile
            captured_create_terminal["working_directory"] = working_directory
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            if parsing_mode == "shadow_only":
                raise AssertionError("shadow_only mode must not call GET /terminals/{id} status")
            return CaoTerminal(
                id=terminal_id,
                name="developer-1",
                provider="codex",
                session_name=str(captured_create_terminal["session_name"]),
                agent_profile="profile",
                status="idle",
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "last"
        ) -> CaoTerminalOutputResponse:
            if mode == "last":
                return CaoTerminalOutputResponse(output="response", mode="last")
            assert mode == "full"
            snapshots = [
                "Codex CLI v0.1.0\n> \n",
                "Codex CLI v0.1.0\n> \n",
                "Codex CLI v0.1.0\n> hello\nassistant> response\n> \n",
            ]
            index = min(self._full_output_calls, len(snapshots) - 1)
            self._full_output_calls += 1
            return CaoTerminalOutputResponse(output=snapshots[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    def _fake_ensure_tmux_available() -> None:
        captured_tmux["available"] = True

    def _fake_create_tmux_session(*, session_name: str, working_directory: Path) -> None:
        captured_tmux["session_name"] = session_name
        captured_tmux["working_directory"] = working_directory

    def _fake_set_tmux_session_environment(*, session_name: str, env_vars: dict[str, str]) -> None:
        captured_tmux["env_session_name"] = session_name
        captured_tmux["env_vars"] = env_vars

    def _fake_list_tmux_windows(*, session_name: str) -> list[object]:
        list_window_calls["count"] += 1
        if list_window_calls["count"] == 1:
            return [
                SimpleNamespace(
                    window_id="@1",
                    window_index="0",
                    window_name="bootstrap-shell",
                )
            ]
        return [
            SimpleNamespace(window_id="@1", window_index="0", window_name="shell"),
            SimpleNamespace(window_id="@2", window_index="1", window_name="developer-1"),
        ]

    def _fake_select_tmux_window(*, window_id: str) -> None:
        selected_window_ids.append(window_id)

    def _fake_kill_tmux_window(*, window_id: str) -> None:
        killed_window_ids.append(window_id)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        _fake_ensure_tmux_available,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        _fake_create_tmux_session,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        _fake_set_tmux_session_environment,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_windows",
        _fake_list_tmux_windows,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._select_tmux_window",
        _fake_select_tmux_window,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._kill_tmux_window",
        _fake_kill_tmux_window,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **kwargs: captured_codex_bootstrap.update(kwargs),
    )

    plan = _sample_launch_plan(tmp_path, tool="codex")
    session = CaoRestSession(
        launch_plan=plan,
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode=parsing_mode,  # type: ignore[arg-type]
        session_manifest_path=tmp_path / "session.json",
        agent_def_dir=tmp_path,
    )

    assert captured_tmux["available"] is True
    assert str(captured_tmux["session_name"]).startswith("AGENTSYS-")
    assert captured_tmux["working_directory"] == tmp_path
    assert captured_tmux["env_session_name"] == captured_tmux["session_name"]
    env_vars = captured_tmux["env_vars"]
    assert isinstance(env_vars, dict)
    assert env_vars["CODEX_HOME"] == str(tmp_path / "home")
    assert env_vars["OPENAI_API_KEY"] == "secret"
    assert env_vars["UNALLOWLISTED_TMUX_VAR"] == "present"
    assert env_vars["INHERITED_CALLER_ENV"] == "caller-value"
    assert env_vars[AGENT_MANIFEST_PATH_ENV_VAR] == str(tmp_path / "session.json")
    assert env_vars[AGENT_DEF_DIR_ENV_VAR] == str(tmp_path.resolve())
    assert captured_codex_bootstrap["home_path"] == tmp_path / "home"
    assert captured_codex_bootstrap["env"]["OPENAI_API_KEY"] == "secret"
    assert captured_codex_bootstrap["working_directory"] == tmp_path
    assert captured_create_terminal["session_name"] == captured_tmux["session_name"]
    assert captured_create_terminal["provider"] == "codex"
    assert captured_create_terminal["working_directory"] == str(tmp_path)
    assert isinstance(captured_create_terminal["agent_profile"], str)
    assert list_window_calls["count"] == 2
    assert selected_window_ids == ["@2"]
    assert killed_window_ids == ["@1"]
    assert session.startup_warnings == ()

    events = session.send_prompt("hello")
    expected_message = "response" if parsing_mode == "cao_only" else "prompt completed"
    assert events[-1].message == expected_message
    done_payload = events[-1].payload or {}
    assert done_payload["parsing_mode"] == parsing_mode
    assert done_payload["output_source_mode"] == ("last" if parsing_mode == "cao_only" else "full")
    assert done_payload["canonical_runtime_status"] == "completed"
    assert "parser_family" in done_payload
    if parsing_mode == "shadow_only":
        assert "output_text" not in done_payload
        assert done_payload["dialog_projection"]["dialog_text"] == "hello\nresponse"
        assert done_payload["surface_assessment"]["business_state"] == "idle"
        assert done_payload["surface_assessment"]["input_mode"] == "freeform"
        assert done_payload["projection_slices"] == {
            "head": "hello\nresponse",
            "tail": "hello\nresponse",
        }


def test_cao_resume_republishes_manifest_and_agent_def_dir_to_tmux_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "agents"
    agent_def_dir.mkdir(parents=True, exist_ok=True)
    captured_tmux_env: dict[str, object] = {}

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda *, session_name, env_vars: captured_tmux_env.update(
            {"session_name": session_name, "env_vars": dict(env_vars)}
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **kwargs: None,
    )

    CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        session_manifest_path=tmp_path / "session.json",
        agent_def_dir=agent_def_dir,
        existing_state=CaoSessionState(
            api_base_url="http://localhost:9889",
            session_name="AGENTSYS-gpu",
            terminal_id="term-123",
            profile_name="runtime-profile",
            profile_path=str(tmp_path / "runtime-profile.md"),
            parsing_mode="shadow_only",
            tmux_window_name="developer-1",
            turn_index=2,
        ),
    )

    assert captured_tmux_env["session_name"] == "AGENTSYS-gpu"
    env_vars = captured_tmux_env["env_vars"]
    assert isinstance(env_vars, dict)
    assert env_vars[AGENT_MANIFEST_PATH_ENV_VAR] == str((tmp_path / "session.json").resolve())
    assert env_vars[AGENT_DEF_DIR_ENV_VAR] == str(agent_def_dir.resolve())


def test_cao_backend_startup_prune_failure_warns_but_keeps_launch_successful(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    selected_window_ids: list[str] = []
    killed_window_ids: list[str] = []
    list_window_calls = {"count": 0}

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            del provider, working_directory
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            return CaoTerminal(
                id=terminal_id,
                name="developer-1",
                provider="codex",
                session_name="s1",
                agent_profile="profile",
                status="idle",
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "last"
        ) -> CaoTerminalOutputResponse:
            return CaoTerminalOutputResponse(output="response", mode=mode)

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    def _fake_list_tmux_windows(*, session_name: str) -> list[object]:
        del session_name
        list_window_calls["count"] += 1
        if list_window_calls["count"] == 1:
            return [SimpleNamespace(window_id="@1", window_index="0", window_name="bootstrap")]
        return [
            SimpleNamespace(window_id="@1", window_index="0", window_name="bootstrap"),
            SimpleNamespace(window_id="@2", window_index="1", window_name="developer-1"),
        ]

    def _fake_select_tmux_window(*, window_id: str) -> None:
        selected_window_ids.append(window_id)

    def _fake_kill_tmux_window(*, window_id: str) -> None:
        killed_window_ids.append(window_id)
        raise BackendExecutionError("permission denied")

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_windows",
        _fake_list_tmux_windows,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._select_tmux_window",
        _fake_select_tmux_window,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._kill_tmux_window",
        _fake_kill_tmux_window,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="cao_only",
        session_manifest_path=tmp_path / "session-prune-fail.json",
    )

    assert session.state.terminal_id == "a1b2c3d4"
    assert selected_window_ids == ["@2"]
    assert killed_window_ids == ["@1"]
    assert len(session.startup_warnings) == 1
    assert "Failed to prune bootstrap tmux window" in session.startup_warnings[0]
    assert "permission denied" in session.startup_warnings[0]


def test_cao_backend_startup_skips_prune_when_bootstrap_and_terminal_share_window(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    selected_window_ids: list[str] = []
    killed_window_ids: list[str] = []
    list_window_calls = {"count": 0}

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            del provider, working_directory
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            return CaoTerminal(
                id=terminal_id,
                name="developer-1",
                provider="codex",
                session_name="s1",
                agent_profile="profile",
                status="idle",
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "last"
        ) -> CaoTerminalOutputResponse:
            return CaoTerminalOutputResponse(output="response", mode=mode)

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    def _fake_list_tmux_windows(*, session_name: str) -> list[object]:
        del session_name
        list_window_calls["count"] += 1
        if list_window_calls["count"] == 1:
            return [SimpleNamespace(window_id="@1", window_index="0", window_name="bootstrap")]
        return [SimpleNamespace(window_id="@1", window_index="0", window_name="developer-1")]

    def _fake_select_tmux_window(*, window_id: str) -> None:
        selected_window_ids.append(window_id)

    def _fake_kill_tmux_window(*, window_id: str) -> None:
        killed_window_ids.append(window_id)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_windows",
        _fake_list_tmux_windows,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._select_tmux_window",
        _fake_select_tmux_window,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._kill_tmux_window",
        _fake_kill_tmux_window,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="cao_only",
        session_manifest_path=tmp_path / "session-same-window.json",
    )

    assert session.state.terminal_id == "a1b2c3d4"
    assert selected_window_ids == ["@1"]
    assert killed_window_ids == []
    assert session.startup_warnings == ()


def test_cao_backend_startup_warns_when_terminal_window_name_never_resolves(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    selected_window_ids: list[str] = []
    killed_window_ids: list[str] = []
    list_window_calls = {"count": 0}

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            del provider, working_directory
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            return CaoTerminal(
                id=terminal_id,
                name="developer-1",
                provider="codex",
                session_name="s1",
                agent_profile="profile",
                status="idle",
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "last"
        ) -> CaoTerminalOutputResponse:
            return CaoTerminalOutputResponse(output="response", mode=mode)

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    def _fake_list_tmux_windows(*, session_name: str) -> list[object]:
        del session_name
        list_window_calls["count"] += 1
        if list_window_calls["count"] == 1:
            return [SimpleNamespace(window_id="@1", window_index="0", window_name="bootstrap")]
        return [
            SimpleNamespace(window_id="@1", window_index="0", window_name="bootstrap"),
            SimpleNamespace(window_id="@2", window_index="1", window_name="other-window"),
        ]

    def _fake_select_tmux_window(*, window_id: str) -> None:
        selected_window_ids.append(window_id)

    def _fake_kill_tmux_window(*, window_id: str) -> None:
        killed_window_ids.append(window_id)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_windows",
        _fake_list_tmux_windows,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._select_tmux_window",
        _fake_select_tmux_window,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._kill_tmux_window",
        _fake_kill_tmux_window,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._TMUX_WINDOW_RESOLVE_MAX_ATTEMPTS",
        3,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._TMUX_WINDOW_RESOLVE_RETRY_SECONDS",
        0.0,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="cao_only",
        session_manifest_path=tmp_path / "session-unresolved-window.json",
    )

    assert session.state.terminal_id == "a1b2c3d4"
    assert selected_window_ids == []
    assert killed_window_ids == []
    assert len(session.startup_warnings) == 1
    warning = session.startup_warnings[0]
    assert "Unable to resolve CAO terminal tmux window" in warning
    assert "after 3 attempts" in warning


def test_cao_backend_resume_uses_existing_state(tmp_path: Path) -> None:
    state = CaoSessionState(
        api_base_url="http://localhost:9889",
        session_name="cao-s1",
        terminal_id="a1b2c3d4",
        profile_name="profile",
        profile_path=str(tmp_path / "profile.md"),
        parsing_mode="cao_only",
        turn_index=3,
    )

    plan = _sample_launch_plan(tmp_path, tool="codex")
    session = CaoRestSession(
        launch_plan=plan,
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="cao_only",
        existing_state=state,
    )
    assert session.state.turn_index == 3
    assert session.state.terminal_id == "a1b2c3d4"


def test_cao_claude_backend_uses_shadow_parsing_with_mode_full_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_sequence = [
        "Claude Code v2.1.62\n❯ \n",
        "Claude Code v2.1.62\n❯ \n",
        "Claude Code v2.1.62\n❯ hello\n✽ Razzmatazzing…\n❯ \n",
        "Claude Code v2.1.62\n❯ hello\n● final answer\n❯ \n",
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self._output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="claude_code",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError(
                "Claude shadow path must not call GET /terminals/{id} status for gating"
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self._output_calls, len(output_sequence) - 1)
            self._output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_claude_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="claude"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        session_manifest_path=tmp_path / "session-claude.json",
    )

    events = session.send_prompt("hello")
    assert events[-1].message == "prompt completed"
    done_payload = events[-1].payload or {}
    assert done_payload["parsing_mode"] == "shadow_only"
    assert done_payload["parser_family"] == "claude_shadow"
    assert "output_text" not in done_payload
    assert done_payload["output_source_mode"] == "full"
    assert done_payload["canonical_runtime_status"] == "completed"
    parser_metadata = done_payload["parser_metadata"]
    assert parser_metadata["shadow_parser_preset"] == "claude_shadow_v2"
    assert parser_metadata["shadow_parser_version"] == "2.1.62"
    assert parser_metadata["shadow_output_format"] == "claude_shadow_v2"
    assert parser_metadata["shadow_output_variant"] == "claude_response_marker_v1"
    assert done_payload["surface_assessment"]["business_state"] == "idle"
    assert done_payload["surface_assessment"]["input_mode"] == "freeform"
    assert done_payload["surface_assessment"]["ui_context"] == "normal_prompt"
    assert done_payload["dialog_projection"]["dialog_text"] == "hello\nfinal answer"
    assert done_payload["projection_slices"] == {
        "head": "hello\nfinal answer",
        "tail": "hello\nfinal answer",
    }
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_claude_shadow_allows_recovered_slash_command_history(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_sequence = [
        ("Claude Code v2.1.62\n❯ /model\n● Set model to Default (claude-sonnet-4-6)\n❯ \n"),
        ("Claude Code v2.1.62\n❯ /model\n● Set model to Default (claude-sonnet-4-6)\n❯ \n"),
        (
            "Claude Code v2.1.62\n"
            "❯ /model\n"
            "● Set model to Default (claude-sonnet-4-6)\n"
            "❯ hello\n"
            "✽ Razzmatazzing…\n"
        ),
        (
            "Claude Code v2.1.62\n"
            "❯ /model\n"
            "● Set model to Default (claude-sonnet-4-6)\n"
            "❯ hello\n"
            "● final answer\n"
            "❯ \n"
        ),
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self.submitted_messages: list[str] = []
            self._output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="claude_code",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError(
                "Claude shadow path must not call GET /terminals/{id} status for gating"
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            self.submitted_messages.append(message)
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self._output_calls, len(output_sequence) - 1)
            self._output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_claude_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="claude"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        session_manifest_path=tmp_path / "session-claude-recovered-slash.json",
    )

    events = session.send_prompt("hello")
    done_payload = events[-1].payload or {}

    assert session._client.submitted_messages == ["hello"]  # noqa: SLF001
    assert done_payload["surface_assessment"]["business_state"] == "idle"
    assert done_payload["surface_assessment"]["input_mode"] == "freeform"
    assert done_payload["surface_assessment"]["ui_context"] == "normal_prompt"
    assert "SLASH_COMMAND_CONTEXT" not in done_payload["surface_assessment"]["evidence"]
    assert done_payload["dialog_projection"]["dialog_text"] == (
        "/model\nSet model to Default (claude-sonnet-4-6)\nhello\nfinal answer"
    )
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_claude_shadow_active_slash_command_surface_blocks_submission(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_clock(monkeypatch, tick_seconds=0.03)

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self.submitted_messages: list[str] = []

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="claude_code",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError(
                "Claude shadow path must not call GET /terminals/{id} status for gating"
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            self.submitted_messages.append(message)
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            return CaoTerminalOutputResponse(
                output="Claude Code v2.1.62\n❯ /model\n",
                mode="full",
            )

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_claude_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="claude"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        poll_interval_seconds=0.0,
        timeout_seconds=0.05,
        session_manifest_path=tmp_path / "session-claude-active-slash.json",
    )

    with pytest.raises(BackendExecutionError, match="Timed out waiting for shadow-ready state"):
        session.send_prompt("hello")

    assert session._client.submitted_messages == []  # noqa: SLF001
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_claude_shadow_baseline_reset_surfaces_current_projection_without_association(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    long_prompt = "previous prompt " * 20
    prior_turn_output = f"Claude Code v2.1.62\n❯ {long_prompt}\n● first answer\n❯ \n"
    output_sequence = [
        prior_turn_output,
        prior_turn_output,
        "Claude Code v2.1.62\n● first answer\n❯ \n",
        "Claude Code v2.1.62\n❯ summarize workspace\n● second answer\n❯ \n",
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self._output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="claude_code",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError(
                "Claude shadow path must not call GET /terminals/{id} status for gating"
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self._output_calls, len(output_sequence) - 1)
            self._output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_claude_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="claude"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        session_manifest_path=tmp_path / "session-claude-baseline-reset.json",
    )

    events = session.send_prompt("summarize workspace")

    assert events[-1].message == "prompt completed"
    done_payload = events[-1].payload or {}
    assert "output_text" not in done_payload
    assert done_payload["dialog_projection"]["dialog_text"] == "first answer"
    assert done_payload["surface_assessment"]["business_state"] == "idle"
    assert done_payload["surface_assessment"]["input_mode"] == "freeform"
    assert done_payload["mode_diagnostics"]["baseline_invalidated"] is True
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_claude_backend_surfaces_waiting_user_answer_as_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_sequence = [
        "Claude Code v2.1.62\n❯ \n",
        "Claude Code v2.1.62\n❯ \n",
        (
            "Claude Code v2.1.62\n"
            "Choose an option:\n"
            "❯ 1. Keep existing changes\n"
            "2. Overwrite and continue\n"
        ),
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self._output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="claude_code",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError(
                "Claude shadow path must not call GET /terminals/{id} status for gating"
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self._output_calls, len(output_sequence) - 1)
            self._output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_claude_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="claude"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        session_manifest_path=tmp_path / "session-claude.json",
    )

    with pytest.raises(BackendExecutionError, match="blocked on operator interaction") as exc_info:
        session.send_prompt("hello")

    assert "1. Keep existing changes" in str(exc_info.value)
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_codex_shadow_backend_uses_runtime_shadow_parser(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_sequence = [
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> hello\nassistant> final answer\n> \n",
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self._output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("Codex shadow path must not call terminal status API")

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self._output_calls, len(output_sequence) - 1)
            self._output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        session_manifest_path=tmp_path / "session-codex-shadow.json",
    )

    events = session.send_prompt("hello")
    assert events[-1].message == "prompt completed"
    done_payload = events[-1].payload or {}
    assert done_payload["parsing_mode"] == "shadow_only"
    assert done_payload["parser_family"] == "codex_shadow"
    assert "output_text" not in done_payload
    parser_metadata = done_payload["parser_metadata"]
    assert parser_metadata["shadow_parser_preset"] == "codex_shadow_v1"
    assert parser_metadata["shadow_parser_version"] == "0.1.0"
    assert parser_metadata["shadow_output_format"] == "codex_shadow_v1"
    assert parser_metadata["shadow_output_variant"] == "codex_label_v1"
    assert parser_metadata["shadow_output_format_match"] is True
    assert parser_metadata["completion_stability_seconds"] == pytest.approx(1.0)
    assert done_payload["mode_diagnostics"]["completion_stability_seconds"] == pytest.approx(1.0)
    assert done_payload["surface_assessment"]["business_state"] == "idle"
    assert done_payload["surface_assessment"]["input_mode"] == "freeform"
    assert done_payload["dialog_projection"]["dialog_text"] == "hello\nfinal answer"
    assert done_payload["projection_slices"] == {
        "head": "hello\nfinal answer",
        "tail": "hello\nfinal answer",
    }
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_codex_shadow_mail_prompt_waits_for_post_submit_sentinel(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    launch_plan = _sample_mailbox_launch_plan(tmp_path, tool="codex")
    prompt_request = prepare_mail_prompt(
        launch_plan=launch_plan,
        operation="send",
        args={
            "to": ["AGENTSYS-orchestrator@agents.localhost"],
            "cc": [],
            "subject": "Investigate parser drift",
            "body_content": "Hello from shadow mode",
            "attachments": [],
        },
    )

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self.output_calls = 0
            self.submitted_request_id: str | None = None

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("shadow_only mode must not call terminal status API")

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            self.submitted_request_id = message.split('"request_id": "', 1)[1].split('"', 1)[0]
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self,
            terminal_id: str,
            mode: str = "full",
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            payload = json.dumps(
                {
                    "ok": True,
                    "request_id": self.submitted_request_id,
                    "operation": "send",
                    "transport": "filesystem",
                    "principal_id": "AGENTSYS-research",
                    "message_id": "msg-20260318T120000Z-shadow",
                }
            )
            output_sequence = [
                "Codex CLI v0.1.0\n> \n",
                "Codex CLI v0.1.0\n> mail send request\nassistant> drafting message\n> \n",
                (
                    "Codex CLI v0.1.0\n"
                    "> mail send request\n"
                    "assistant> drafting message\n"
                    "AGENTSYS_MAIL_RESULT_BEGIN\n"
                    f"{payload}\n"
                    "AGENTSYS_MAIL_RESULT_END\n"
                    "> \n"
                ),
            ]
            index = min(self.output_calls, len(output_sequence) - 1)
            self.output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=launch_plan,
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        poll_interval_seconds=0.0,
        session_manifest_path=tmp_path / "session-codex-shadow-mail.json",
    )

    events = session.send_mail_prompt(prompt_request)
    mailbox = launch_plan.mailbox
    assert mailbox is not None
    payload = parse_mail_result(
        events,
        request_id=prompt_request.request_id,
        operation=prompt_request.operation,
        mailbox=mailbox,
    )
    done_payload = events[-1].payload or {}

    assert payload["message_id"] == "msg-20260318T120000Z-shadow"
    assert done_payload["canonical_runtime_status"] == "completed"
    assert "mail_result_surfaces" in done_payload
    assert session._client.output_calls == 3  # noqa: SLF001
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_codex_shadow_mail_prompt_detects_result_while_shadow_stays_working(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    launch_plan = _sample_mailbox_launch_plan(tmp_path, tool="codex")
    prompt_request = prepare_mail_prompt(
        launch_plan=launch_plan,
        operation="send",
        args={
            "to": ["AGENTSYS-orchestrator@agents.localhost"],
            "cc": [],
            "subject": "Investigate parser drift",
            "body_content": "Hello from shadow mode",
            "attachments": [],
        },
    )

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self.output_calls = 0
            self.submitted_request_id: str | None = None

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("mail result observation should not need terminal status polling")

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            self.submitted_request_id = message.split('"request_id": "', 1)[1].split('"', 1)[0]
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self,
            terminal_id: str,
            mode: str = "full",
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            payload = json.dumps(
                {
                    "ok": True,
                    "request_id": self.submitted_request_id,
                    "operation": "send",
                    "transport": "filesystem",
                    "principal_id": "AGENTSYS-research",
                    "message_id": "msg-20260318T120000Z-shadow",
                }
            )
            output_sequence = [
                "Codex CLI v0.1.0\n> \n",
                "Codex CLI v0.1.0\nprocessing send request\nassistant> drafting message\n> \n",
                (
                    "Codex CLI v0.1.0\n"
                    "processing send request\n"
                    "assistant> drafting message\n"
                    "AGENTSYS_MAIL_RESULT_BEGIN\n"
                    f"{payload}\n"
                    "AGENTSYS_MAIL_RESULT_END\n"
                    "> \n"
                ),
            ]
            index = min(self.output_calls, len(output_sequence) - 1)
            self.output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=launch_plan,
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        poll_interval_seconds=0.0,
        session_manifest_path=tmp_path / "session-codex-shadow-mail-ready.json",
    )

    events = session.send_mail_prompt(prompt_request)
    mailbox = launch_plan.mailbox
    assert mailbox is not None
    payload = parse_mail_result(
        events,
        request_id=prompt_request.request_id,
        operation=prompt_request.operation,
        mailbox=mailbox,
    )
    done_payload = events[-1].payload or {}

    assert payload["message_id"] == "msg-20260318T120000Z-shadow"
    assert done_payload["canonical_runtime_status"] == "completed"
    assert "mail_result_surfaces" in done_payload
    assert session._client.output_calls == 3  # noqa: SLF001
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_codex_shadow_backend_surfaces_waiting_user_answer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output_sequence = [
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> \n",
        (
            "Codex CLI v0.1.0\n"
            "Choose an option:\n"
            "❯ 1. Keep existing changes\n"
            "2. Overwrite and continue\n"
        ),
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self._output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("Codex shadow path must not call terminal status API")

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self._output_calls, len(output_sequence) - 1)
            self._output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        session_manifest_path=tmp_path / "session-codex-shadow-waiting.json",
    )

    with pytest.raises(BackendExecutionError, match="blocked on operator interaction") as exc_info:
        session.send_prompt("hello")
    assert "1. Keep existing changes" in str(exc_info.value)
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_codex_shadow_reports_readiness_stalled_entry_and_recovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_clock(monkeypatch, tick_seconds=0.03)
    output_sequence = [
        "OpenAI Codex (v0.98.0)\nYou requested a status summary\n",
        "OpenAI Codex (v0.98.0)\nYou requested a status summary\n",
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> hello\nassistant> final answer\n> \n",
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self._output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("shadow_only mode must not call terminal status API")

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self._output_calls, len(output_sequence) - 1)
            self._output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_shadow_policy_launch_plan(
            tmp_path,
            unknown_timeout_seconds=0.02,
            completion_stability_seconds=0.06,
            stalled_is_terminal=False,
        ),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        poll_interval_seconds=0.0,
        session_manifest_path=tmp_path / "session-codex-readiness-stalled.json",
    )

    events = session.send_prompt("hello")
    done_payload = events[-1].payload or {}
    anomalies = done_payload["parser_metadata"]["shadow_parser_anomalies"]
    anomaly_codes = {item["code"] for item in anomalies}

    assert done_payload["canonical_runtime_status"] == "completed"
    assert done_payload["mode_diagnostics"]["completion_stability_seconds"] == pytest.approx(0.06)
    assert done_payload["parser_metadata"]["completion_stability_seconds"] == pytest.approx(0.06)
    assert ANOMALY_STALLED_ENTERED in anomaly_codes
    assert ANOMALY_STALLED_RECOVERED in anomaly_codes
    assert any(
        item["code"] == ANOMALY_STALLED_ENTERED and item["details"].get("phase") == "readiness"
        for item in anomalies
    )
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_codex_shadow_terminal_stalled_fails_without_cross_mode_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_clock(monkeypatch, tick_seconds=0.03)
    output_sequence = [
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> \n",
        "OpenAI Codex (v0.98.0)\nYou requested a status summary\n",
        "OpenAI Codex (v0.98.0)\nYou requested a status summary\n",
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self._output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("shadow_only mode must not call terminal status API")

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self._output_calls, len(output_sequence) - 1)
            self._output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_shadow_policy_launch_plan(
            tmp_path,
            unknown_timeout_seconds=0.02,
            completion_stability_seconds=0.06,
            stalled_is_terminal=True,
        ),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        poll_interval_seconds=0.0,
        session_manifest_path=tmp_path / "session-codex-terminal-stalled.json",
    )

    with pytest.raises(BackendExecutionError, match="stalled state"):
        session.send_prompt("hello")
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_codex_shadow_non_terminal_stalled_recovers_and_completes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_fake_clock(monkeypatch, tick_seconds=0.03)
    output_sequence = [
        "Codex CLI v0.1.0\n> \n",
        "Codex CLI v0.1.0\n> \n",
        "OpenAI Codex (v0.98.0)\nYou requested a status summary\n",
        "OpenAI Codex (v0.98.0)\nYou requested a status summary\n",
        "Codex CLI v0.1.0\n> hello\nassistant> final answer\n> \n",
    ]

    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self._output_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("shadow_only mode must not call terminal status API")

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            index = min(self._output_calls, len(output_sequence) - 1)
            self._output_calls += 1
            return CaoTerminalOutputResponse(output=output_sequence[index], mode="full")

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.ensure_codex_home_bootstrap",
        lambda **_: None,
    )

    session = CaoRestSession(
        launch_plan=_sample_shadow_policy_launch_plan(
            tmp_path,
            unknown_timeout_seconds=0.02,
            completion_stability_seconds=0.06,
            stalled_is_terminal=False,
        ),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        poll_interval_seconds=0.0,
        session_manifest_path=tmp_path / "session-codex-non-terminal-stalled.json",
    )

    events = session.send_prompt("hello")
    done_payload = events[-1].payload or {}
    anomalies = done_payload["parser_metadata"]["shadow_parser_anomalies"]
    anomaly_codes = {item["code"] for item in anomalies}

    assert done_payload["canonical_runtime_status"] == "completed"
    assert done_payload["mode_diagnostics"]["completion_stability_seconds"] == pytest.approx(0.06)
    assert done_payload["parser_metadata"]["completion_stability_seconds"] == pytest.approx(0.06)
    assert ANOMALY_STALLED_ENTERED in anomaly_codes
    assert ANOMALY_STALLED_RECOVERED in anomaly_codes
    assert any(
        item["code"] == ANOMALY_STALLED_ENTERED and item["details"].get("phase") == "completion"
        for item in anomalies
    )
    assert any(
        item["code"] == ANOMALY_STALLED_RECOVERED
        and item["details"].get("recovered_to") == "completed"
        for item in anomalies
    )
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_backend_rejects_unknown_parsing_mode(tmp_path: Path) -> None:
    with pytest.raises(BackendExecutionError, match="Unsupported CAO parsing mode"):
        CaoRestSession(
            launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
            api_base_url="http://localhost:9889",
            role_name="gpu-kernel-coder",
            role_prompt="role prompt",
            parsing_mode="hybrid",  # type: ignore[arg-type]
            session_manifest_path=tmp_path / "session.json",
        )


def test_shadow_only_codex_failure_does_not_fallback_to_cao_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            raise AssertionError("shadow_only mode must not call terminal status API")

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "full"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "full"
            return CaoTerminalOutputResponse(
                output="unexpected output shape",
                mode="full",
            )

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="shadow_only",
        session_manifest_path=tmp_path / "session-codex-shadow.json",
    )

    with pytest.raises(BackendExecutionError, match="unsupported_output_format"):
        session.send_prompt("hello")
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_cao_only_failure_does_not_fallback_to_mode_full(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class _FakeClient:
        def __init__(self, base_url: str, timeout_seconds: float = 15.0) -> None:
            self.base_url = base_url
            self.timeout_seconds = timeout_seconds
            self.requested_modes: list[str] = []
            self._status_calls = 0

        def health(self) -> CaoHealthResponse:
            return CaoHealthResponse(status="ok", service="cli-agent-orchestrator")

        def create_terminal(
            self,
            session_name: str,
            *,
            provider: str,
            agent_profile: str,
            working_directory: str | None = None,
        ) -> CaoTerminal:
            return CaoTerminal(
                id="a1b2c3d4",
                name="developer-1",
                provider="codex",
                session_name=session_name,
                agent_profile=agent_profile,
                status="idle",
            )

        def get_terminal(self, terminal_id: str) -> CaoTerminal:
            statuses = ["idle", "completed"]
            index = min(self._status_calls, len(statuses) - 1)
            self._status_calls += 1
            return CaoTerminal(
                id=terminal_id,
                name="developer-1",
                provider="codex",
                session_name="s1",
                agent_profile="profile",
                status=statuses[index],
            )

        def send_terminal_input(self, terminal_id: str, message: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def get_terminal_output(
            self, terminal_id: str, mode: str = "last"
        ) -> CaoTerminalOutputResponse:
            self.requested_modes.append(mode)
            assert mode == "last"
            raise CaoApiError(
                method="GET",
                url="http://localhost:9889/terminals/a1b2c3d4/output?mode=last",
                detail="mode=last unavailable",
                status_code=404,
            )

        def exit_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_terminal(self, terminal_id: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

        def delete_session(self, session_name: str) -> CaoSuccessResponse:
            return CaoSuccessResponse(success=True)

    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest.CaoRestClient",
        _FakeClient,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._create_tmux_session",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._set_tmux_session_environment",
        lambda **_: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: set(),
    )

    session = CaoRestSession(
        launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
        api_base_url="http://localhost:9889",
        role_name="gpu-kernel-coder",
        role_prompt="role prompt",
        parsing_mode="cao_only",
        session_manifest_path=tmp_path / "session-codex-cao.json",
    )

    with pytest.raises(BackendExecutionError, match="mode=last"):
        session.send_prompt("hello")
    assert session._client.requested_modes == ["last"]  # noqa: SLF001


def test_generate_cao_session_name_adds_conflict_suffix() -> None:
    occupied = {"AGENTSYS-codex-gpu-kernel-coder"}
    generated = generate_cao_session_name(
        tool="codex",
        role_name="gpu-kernel-coder",
        existing_sessions=occupied,
    )
    expected_agent_id = derive_agent_id_from_name("AGENTSYS-codex-gpu-kernel-coder")
    assert generated == f"AGENTSYS-codex-gpu-kernel-coder-{expected_agent_id[:6]}"


def test_cao_backend_rejects_conflicting_explicit_agent_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._ensure_tmux_available",
        lambda: None,
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.cao_rest._list_tmux_sessions",
        lambda: {"AGENTSYS-gpu"},
    )

    with pytest.raises(BackendExecutionError, match="already in use"):
        CaoRestSession(
            launch_plan=_sample_launch_plan(tmp_path, tool="codex"),
            api_base_url="http://localhost:9889",
            role_name="gpu-kernel-coder",
            role_prompt="role prompt",
            parsing_mode="cao_only",
            session_manifest_path=tmp_path / "session.json",
            agent_identity="gpu",
        )
