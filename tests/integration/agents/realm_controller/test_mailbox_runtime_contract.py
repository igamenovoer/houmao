from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from houmao.agents.brain_builder import BuildRequest, build_brain_home
from houmao.agents.mailbox_runtime_support import (
    mailbox_env_bindings,
    main as mailbox_runtime_main,
)
from houmao.agents.realm_controller import cli
from houmao.agents.realm_controller.agent_identity import derive_agent_id_from_name
from houmao.agents.realm_controller.backends.cao_rest import CaoRestSession
from houmao.agents.realm_controller.gateway_models import GatewayCurrentInstanceV1
from houmao.agents.realm_controller.gateway_storage import (
    AGENT_GATEWAY_HOST_ENV_VAR,
    AGENT_GATEWAY_PORT_ENV_VAR,
    AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR,
    AGENT_GATEWAY_STATE_PATH_ENV_VAR,
    gateway_paths_from_manifest_path,
    write_gateway_current_instance,
)
from houmao.agents.realm_controller.launch_plan import LaunchPlanRequest, build_launch_plan
from houmao.agents.realm_controller.loaders import load_brain_manifest, load_role_package
from houmao.agents.realm_controller.mail_commands import prepare_mail_prompt, run_mail_prompt
from houmao.agents.realm_controller.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
    default_manifest_path,
    write_session_manifest,
)
from houmao.agents.realm_controller.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionEvent,
)
from houmao.agents.realm_controller.runtime import (
    resume_runtime_session,
    start_runtime_session,
)
from houmao.agents.mailbox_runtime_models import (
    FilesystemMailboxDeclarativeConfig,
    FilesystemMailboxResolvedConfig,
)
from houmao.agents.launch_policy.models import LaunchPolicyResult
from houmao.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox
from houmao.cao.models import (
    CaoHealthResponse,
    CaoSuccessResponse,
    CaoTerminal,
    CaoTerminalOutputResponse,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_agent_def_dir(agent_def_dir: Path) -> None:
    _write(
        agent_def_dir / "tools/codex/adapter.yaml",
        """
schema_version: 1
tool: codex
home_selector:
  env_var: CODEX_HOME
launch:
  executable: codex
  args: []
  env_injection:
    mode: home_dotenv
    env_file_in_home: .env
config_projection:
  destination: .
skills_projection:
  destination: skills
  mode: symlink
credential_projection:
  files_dir: files
  file_mappings: []
  env:
    source: env/vars.env
    allowlist:
      - OPENAI_API_KEY
""".strip()
        + "\n",
    )
    _write(agent_def_dir / "skills/skill-a/SKILL.md", "# skill-a\n")
    _write(agent_def_dir / "tools/codex/setups/default/config.toml", "model='x'\n")
    _write(
        agent_def_dir / "tools/codex/auth/personal-a/env/vars.env",
        "OPENAI_API_KEY=sk-test-123\n",
    )
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")


def _mailbox_launch_plan(tmp_path: Path) -> LaunchPlan:
    mailbox_root = tmp_path / "mailbox"
    principal_id = "HOUMAO-research"
    address = "HOUMAO-research@agents.localhost"
    bootstrap_filesystem_mailbox(
        mailbox_root,
        principal=MailboxPrincipal(principal_id=principal_id, address=address),
    )
    mailbox = FilesystemMailboxResolvedConfig(
        transport="filesystem",
        principal_id=principal_id,
        address=address,
        filesystem_root=mailbox_root.resolve(),
        bindings_version="2026-03-12T05:00:00.000001Z",
    )
    return LaunchPlan(
        backend="codex_headless",
        tool="codex",
        executable="codex",
        args=[],
        working_directory=tmp_path,
        home_env_var="CODEX_HOME",
        home_path=tmp_path / "home",
        env=mailbox_env_bindings(mailbox),
        env_var_names=sorted(mailbox_env_bindings(mailbox).keys()),
        role_injection=RoleInjectionPlan(
            method="native_developer_instructions",
            role_name="r",
            prompt="Role prompt",
        ),
        metadata={},
        mailbox=mailbox,
    )


def _mailbox_cao_launch_plan(tmp_path: Path) -> LaunchPlan:
    launch_plan = _mailbox_launch_plan(tmp_path)
    return replace(launch_plan, backend="cao_rest")


def test_mailbox_runtime_contract_covers_build_start_refresh_and_resume(
    monkeypatch,
    tmp_path: Path,
) -> None:
    agent_def_dir = tmp_path / "repo"
    runtime_root = tmp_path / "runtime"
    _seed_agent_def_dir(agent_def_dir)

    build_result = build_brain_home(
        BuildRequest(
            agent_def_dir=agent_def_dir,
            runtime_root=runtime_root,
            tool="codex",
            skills=["skill-a"],
            setup="default",
            auth="personal-a",
            mailbox=FilesystemMailboxDeclarativeConfig(
                transport="filesystem",
                principal_id="HOUMAO-research",
                address="HOUMAO-research@agents.localhost",
                filesystem_root="shared-mail",
            ),
            home_id="mailbox-brain-001",
        )
    )

    visible_gateway_skill = (
        build_result.home_path / "skills/mailbox/houmao-email-via-agent-gateway/SKILL.md"
    )
    visible_skill = build_result.home_path / "skills/mailbox/houmao-email-via-filesystem/SKILL.md"
    assert visible_gateway_skill.is_file()
    assert visible_skill.is_file()
    assert not (
        build_result.home_path / "skills/.system/mailbox/houmao-email-via-filesystem/SKILL.md"
    ).exists()

    class _FakeStartBackend:
        def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
            self.launch_plan = launch_plan

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        lambda **kwargs: _FakeStartBackend(),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.launch_plan.apply_launch_policy",
        lambda request: LaunchPolicyResult(
            executable=request.executable,
            args=request.base_args,
            provenance=None,
            strategy=None,
        ),
    )

    controller = start_runtime_session(
        agent_def_dir=agent_def_dir,
        brain_manifest_path=build_result.manifest_path,
        role_name="r",
        runtime_root=runtime_root,
        backend="codex_app_server",
        working_directory=tmp_path,
    )

    mailbox = controller.launch_plan.mailbox
    assert mailbox is not None
    assert (mailbox.filesystem_root / "rules/scripts/requirements.txt").is_file()
    assert (
        mailbox.filesystem_root / "mailboxes/HOUMAO-research@agents.localhost/archive"
    ).is_dir()
    assert (
        mailbox.filesystem_root
        / "mailboxes"
        / "HOUMAO-research@agents.localhost"
        / "mailbox.sqlite"
    ).is_file()

    refreshed = controller.refresh_mailbox_bindings(
        filesystem_root=runtime_root / "refreshed-mail",
    )
    persisted = json.loads(controller.manifest_path.read_text(encoding="utf-8"))
    assert persisted["launch_plan"]["mailbox"]["filesystem_root"] == str(refreshed.filesystem_root)
    assert (refreshed.filesystem_root / "rules/scripts/deliver_message.py").is_file()

    manifest = load_brain_manifest(build_result.manifest_path)
    role = load_role_package(agent_def_dir, "r")
    resumed_launch_plan = build_launch_plan(
        LaunchPlanRequest(
            brain_manifest=manifest,
            role_package=role,
            backend="codex_headless",
            working_directory=tmp_path,
            mailbox=refreshed,
        )
    )
    session_payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=resumed_launch_plan,
            role_name="r",
            brain_manifest_path=build_result.manifest_path,
            agent_name="HOUMAO-research",
            backend_state={
                "session_id": "sess-1",
                "turn_index": 1,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-research",
            },
        )
    )
    session_path = tmp_path / "resumed-session.json"
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    captured: dict[str, LaunchPlan] = {}

    def _fake_resume_backend(**kwargs: object) -> object:
        captured["launch_plan"] = kwargs["launch_plan"]  # type: ignore[index]
        return object()

    monkeypatch.setattr(
        "houmao.agents.realm_controller.runtime._create_backend_session",
        _fake_resume_backend,
    )

    resumed = resume_runtime_session(
        agent_def_dir=agent_def_dir,
        session_manifest_path=session_path,
    )

    assert resumed.launch_plan.mailbox is not None
    assert resumed.launch_plan.mailbox.filesystem_root == refreshed.filesystem_root
    assert captured["launch_plan"].mailbox == resumed.launch_plan.mailbox


def test_mailbox_runtime_contract_mail_send_and_reply_via_cli(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    launch_plan = _mailbox_launch_plan(tmp_path)
    body_file = tmp_path / "body.md"
    body_file.write_text("# Hello\n", encoding="utf-8")
    attachment = tmp_path / "attachment.txt"
    attachment.write_text("attachment\n", encoding="utf-8")
    prompts: list[str] = []

    class _FakeController:
        def __init__(self) -> None:
            self.launch_plan = launch_plan

        def send_prompt(self, prompt: str) -> list[SessionEvent]:
            prompts.append(prompt)
            request_id = prompt.split('"request_id": "', 1)[1].split('"', 1)[0]
            operation = "reply" if '"operation": "reply"' in prompt else "send"
            return [
                SessionEvent(
                    kind="assistant",
                    message=(
                        "HOUMAO_MAIL_RESULT_BEGIN\n"
                        + json.dumps(
                            {
                                "ok": True,
                                "request_id": request_id,
                                "operation": operation,
                                "transport": "filesystem",
                                "principal_id": "HOUMAO-research",
                            }
                        )
                        + "\nHOUMAO_MAIL_RESULT_END"
                    ),
                    turn_index=1,
                )
            ]

    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            agent_def_dir=(tmp_path / "resolved-agent-def").resolve(),
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "houmao.agents.realm_controller.cli.resume_runtime_session",
        lambda **kwargs: _FakeController(),
    )

    send_exit = cli.main(
        [
            "mail",
            "send",
            "--agent-identity",
            "HOUMAO-research",
            "--to",
            "HOUMAO-orchestrator@agents.localhost",
            "--subject",
            "Investigate parser drift",
            "--body-file",
            str(body_file),
            "--attach",
            str(attachment),
        ]
    )
    reply_exit = cli.main(
        [
            "mail",
            "reply",
            "--agent-identity",
            "HOUMAO-research",
            "--message-ref",
            "filesystem:msg-20260312T050000Z-parent",
            "--body-content",
            "Reply with next steps",
        ]
    )

    assert send_exit == 0
    assert reply_exit == 0
    assert "# Hello" in prompts[0]
    assert str(attachment.resolve()) in prompts[0]
    assert '"message_ref": "filesystem:msg-20260312T050000Z-parent"' in prompts[1]
    assert '"body_content": "Reply with next steps"' in prompts[1]
    assert '"instruction"' not in prompts[1]

    output = capsys.readouterr().out
    assert '"operation": "send"' in output
    assert '"operation": "reply"' in output


def test_mailbox_runtime_contract_mail_send_waits_for_delayed_shadow_sentinel(
    monkeypatch,
    tmp_path: Path,
) -> None:
    launch_plan = _mailbox_cao_launch_plan(tmp_path)
    prompt_request = prepare_mail_prompt(
        launch_plan=launch_plan,
        operation="send",
        args={
            "to": ["HOUMAO-orchestrator@agents.localhost"],
            "cc": [],
            "subject": "Investigate parser drift",
            "body_content": "Hello from integration coverage",
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
                    "principal_id": "HOUMAO-research",
                    "message_ref": "filesystem:msg-20260318T130000Z-integration",
                }
            )
            output_sequence = [
                "Codex CLI v0.1.0\n> \n",
                "Codex CLI v0.1.0\n> mail send request\nassistant> drafting message\n> \n",
                (
                    "Codex CLI v0.1.0\n"
                    "> mail send request\n"
                    "assistant> drafting message\n"
                    "HOUMAO_MAIL_RESULT_BEGIN\n"
                    f"{payload}\n"
                    "HOUMAO_MAIL_RESULT_END\n"
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
    mailbox = launch_plan.mailbox
    assert mailbox is not None

    result = run_mail_prompt(
        send_prompt=None,
        send_mail_prompt=session.send_mail_prompt,
        prompt_request=prompt_request,
        mailbox=mailbox,
    )

    assert result["authoritative"] is False
    assert result["status"] == "submitted"
    assert result["execution_path"] == "tui_submission"
    assert result["preview_result"]["message_ref"] == "filesystem:msg-20260318T130000Z-integration"
    assert session._client.output_calls == 3  # noqa: SLF001
    assert set(session._client.requested_modes) == {"full"}  # noqa: SLF001


def test_resolve_live_cli_surfaces_attached_gateway_base_url_for_mailbox_work(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    launch_plan = _mailbox_launch_plan(tmp_path)
    mailbox = launch_plan.mailbox
    assert mailbox is not None
    manifest_path = default_manifest_path(tmp_path, "codex_headless", "codex-headless-1")
    payload = build_session_manifest_payload(
        SessionManifestRequest(
            launch_plan=launch_plan,
            role_name="r",
            brain_manifest_path=tmp_path / "brain.yaml",
            agent_name="research",
            agent_id=derive_agent_id_from_name("research"),
            tmux_session_name="HOUMAO-research",
            backend_state={
                "session_id": "sess-1",
                "turn_index": 1,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "HOUMAO-research",
            },
        )
    )
    write_session_manifest(manifest_path, payload)
    paths = gateway_paths_from_manifest_path(manifest_path)
    assert paths is not None
    write_gateway_current_instance(
        paths.current_instance_path,
        GatewayCurrentInstanceV1(
            pid=4242,
            host="127.0.0.1",
            port=43123,
            managed_agent_instance_epoch=1,
        ),
    )
    tmux_env = {
        **mailbox_env_bindings(mailbox),
        AGENT_GATEWAY_HOST_ENV_VAR: "127.0.0.1",
        AGENT_GATEWAY_PORT_ENV_VAR: "43123",
        AGENT_GATEWAY_STATE_PATH_ENV_VAR: str(paths.state_path),
        AGENT_GATEWAY_PROTOCOL_VERSION_ENV_VAR: "v1",
    }
    monkeypatch.setattr(
        "houmao.agents.realm_controller.backends.tmux_runtime.read_tmux_session_environment_value",
        lambda *, session_name, variable_name: tmux_env.get(variable_name),
    )

    class _FakeGatewayClient:
        def __init__(self, *, endpoint, timeout_seconds: float = 5.0) -> None:
            del timeout_seconds
            self.m_endpoint = endpoint

        def health(self):
            return SimpleNamespace(protocol_version="v1", status="ok")

    monkeypatch.setattr("houmao.agents.mailbox_runtime_support.GatewayClient", _FakeGatewayClient)

    exit_code = mailbox_runtime_main(["resolve-live", "--manifest-path", str(manifest_path)])
    captured = capsys.readouterr()
    resolved = json.loads(captured.out)

    assert exit_code == 0
    assert resolved["mailbox"]["transport"] == "filesystem"
    assert resolved["gateway"]["source"] == "current_instance_record"
    assert resolved["gateway"]["base_url"] == "http://127.0.0.1:43123"
    assert resolved["gateway"]["state_path"] == str(paths.state_path)
