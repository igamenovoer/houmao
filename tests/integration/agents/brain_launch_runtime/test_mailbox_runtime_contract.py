from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from gig_agents.agents.brain_builder import BuildRequest, build_brain_home
from gig_agents.agents.brain_launch_runtime import cli
from gig_agents.agents.brain_launch_runtime.launch_plan import LaunchPlanRequest, build_launch_plan
from gig_agents.agents.brain_launch_runtime.loaders import load_brain_manifest, load_role_package
from gig_agents.agents.brain_launch_runtime.manifest import (
    SessionManifestRequest,
    build_session_manifest_payload,
)
from gig_agents.agents.brain_launch_runtime.models import (
    LaunchPlan,
    RoleInjectionPlan,
    SessionEvent,
)
from gig_agents.agents.brain_launch_runtime.runtime import (
    resume_runtime_session,
    start_runtime_session,
)
from gig_agents.agents.mailbox_runtime_models import (
    MailboxDeclarativeConfig,
    MailboxResolvedConfig,
)
from gig_agents.agents.mailbox_runtime_support import mailbox_env_bindings
from gig_agents.mailbox import MailboxPrincipal, bootstrap_filesystem_mailbox


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_agent_def_dir(agent_def_dir: Path) -> None:
    _write(
        agent_def_dir / "brains/tool-adapters/codex.yaml",
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
    _write(agent_def_dir / "brains/skills/skill-a/SKILL.md", "# skill-a\n")
    _write(agent_def_dir / "brains/cli-configs/codex/default/config.toml", "model='x'\n")
    _write(
        agent_def_dir / "brains/api-creds/codex/personal-a/env/vars.env",
        "OPENAI_API_KEY=sk-test-123\n",
    )
    _write(agent_def_dir / "roles/r/system-prompt.md", "Role prompt\n")


def _mailbox_launch_plan(tmp_path: Path) -> LaunchPlan:
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
            config_profile="default",
            credential_profile="personal-a",
            mailbox=MailboxDeclarativeConfig(
                transport="filesystem",
                principal_id="AGENTSYS-research",
                address="AGENTSYS-research@agents.localhost",
                filesystem_root="shared-mail",
            ),
            home_id="mailbox-brain-001",
        )
    )

    assert (
        build_result.home_path / "skills/.system/mailbox/email-via-filesystem/SKILL.md"
    ).is_file()

    class _FakeStartBackend:
        def update_launch_plan(self, launch_plan: LaunchPlan) -> None:
            self.launch_plan = launch_plan

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.runtime._create_backend_session",
        lambda **kwargs: _FakeStartBackend(),
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
        mailbox.filesystem_root / "mailboxes/AGENTSYS-research@agents.localhost/archive"
    ).is_dir()

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
            backend_state={
                "session_id": "sess-1",
                "turn_index": 1,
                "role_bootstrap_applied": True,
                "working_directory": str(tmp_path),
                "tmux_session_name": "AGENTSYS-research",
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
        "gig_agents.agents.brain_launch_runtime.runtime._create_backend_session",
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
                        "AGENTSYS_MAIL_RESULT_BEGIN\n"
                        + json.dumps(
                            {
                                "ok": True,
                                "request_id": request_id,
                                "operation": operation,
                                "transport": "filesystem",
                                "principal_id": "AGENTSYS-research",
                            }
                        )
                        + "\nAGENTSYS_MAIL_RESULT_END"
                    ),
                    turn_index=1,
                )
            ]

    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.resolve_agent_identity",
        lambda **kwargs: SimpleNamespace(
            session_manifest_path=tmp_path / "session.json",
            agent_def_dir=(tmp_path / "resolved-agent-def").resolve(),
            warnings=(),
        ),
    )
    monkeypatch.setattr(
        "gig_agents.agents.brain_launch_runtime.cli.resume_runtime_session",
        lambda **kwargs: _FakeController(),
    )

    send_exit = cli.main(
        [
            "mail",
            "send",
            "--agent-identity",
            "AGENTSYS-research",
            "--to",
            "AGENTSYS-orchestrator@agents.localhost",
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
            "AGENTSYS-research",
            "--message-id",
            "msg-20260312T050000Z-parent",
            "--body-content",
            "Reply with next steps",
        ]
    )

    assert send_exit == 0
    assert reply_exit == 0
    assert "# Hello" in prompts[0]
    assert str(attachment.resolve()) in prompts[0]
    assert '"message_id": "msg-20260312T050000Z-parent"' in prompts[1]
    assert '"body_content": "Reply with next steps"' in prompts[1]
    assert '"instruction"' not in prompts[1]

    output = capsys.readouterr().out
    assert '"operation": "send"' in output
    assert '"operation": "reply"' in output
