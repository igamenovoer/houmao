from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

import houmao.agents.realm_controller.backends.headless_base as headless_base
from houmao.agents.realm_controller.backends.headless_base import HeadlessSessionState
from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessCliRunner,
    HeadlessRunResult,
)
from houmao.agents.realm_controller.backends.kimi_headless import KimiHeadlessSession
from houmao.agents.realm_controller.models import LaunchPlan, RoleInjectionPlan


def test_fake_kimi_stream_json_persists_session_and_resumes_by_exact_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    fake_kimi = tmp_path / "fake-bin" / "kimi"
    arg_log = tmp_path / "kimi-argv.tsv"
    fake_kimi.parent.mkdir(parents=True)
    fake_kimi.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                'printf "ARGV" >> "$KIMI_ARG_LOG"',
                'for arg in "$@"; do',
                "  escaped=${arg//$'\\n'/\\\\n}",
                "  escaped=${escaped//$'\\t'/\\\\t}",
                '  printf "\\t%s" "$escaped" >> "$KIMI_ARG_LOG"',
                "done",
                'printf "\\n" >> "$KIMI_ARG_LOG"',
                'echo \'{"role":"assistant","content":"ok"}\'',
                (
                    'echo \'{"role":"meta","type":"session.resume_hint",'
                    '"session_id":"session_fake_1"}\''
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_kimi.chmod(0o755)
    monkeypatch.setattr(headless_base, "ensure_tmux_available_shared", lambda: None)
    monkeypatch.setattr(
        headless_base,
        "generate_tmux_session_name_shared",
        lambda *, tool, role_name: "HOUMAO-kimi-fake",
    )
    monkeypatch.setattr(
        headless_base,
        "has_tmux_session_shared",
        lambda *, session_name: subprocess.CompletedProcess(
            args=["tmux", "has-session", "-t", session_name],
            returncode=1,
            stdout="",
            stderr="",
        ),
    )
    monkeypatch.setattr(headless_base, "create_tmux_session_shared", lambda **_kwargs: None)
    monkeypatch.setattr(
        headless_base,
        "prepare_headless_agent_window_shared",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        headless_base,
        "set_tmux_session_environment_shared",
        lambda **_kwargs: None,
    )

    session = KimiHeadlessSession(
        launch_plan=LaunchPlan(
            backend="kimi_headless",
            tool="kimi",
            executable=str(fake_kimi),
            args=[],
            working_directory=tmp_path,
            home_env_var="KIMI_CODE_HOME",
            home_path=tmp_path / "kimi-home",
            env={"KIMI_ARG_LOG": str(arg_log)},
            env_var_names=["KIMI_ARG_LOG"],
            role_injection=RoleInjectionPlan(
                method="bootstrap_message",
                role_name="coder",
                prompt="role prompt",
                bootstrap_message="bootstrap",
            ),
            metadata={},
        ),
        role_name="coder",
        session_manifest_path=tmp_path / "session.json",
        state=HeadlessSessionState(
            working_directory=str(tmp_path),
        ),
    )
    direct_runner = HeadlessCliRunner()

    class _DirectRunner:
        def run(  # type: ignore[no-untyped-def]
            self,
            *,
            command,
            env,
            cwd,
            turn_index,
            output_format,
            tmux_session_name,
            turn_artifacts_root,
            turn_artifact_dir_name=None,
            **_kwargs,
        ) -> HeadlessRunResult:
            del tmux_session_name, turn_artifacts_root, turn_artifact_dir_name
            return direct_runner.run(
                command=command,
                env=env,
                cwd=cwd,
                turn_index=turn_index,
                output_format=output_format,
                provider="kimi",
            )

    session._runner = _DirectRunner()  # type: ignore[attr-defined]

    session.send_prompt("first")
    session.send_prompt("second")

    invocations = [
        line.split("\t")[1:]
        for line in arg_log.read_text(encoding="utf-8").splitlines()
        if line.startswith("ARGV\t")
    ]

    assert session.state.session_id == "session_fake_1"
    assert invocations[0] == [
        "--skills-dir",
        str(tmp_path / "kimi-home" / "skills"),
        "-p",
        r"bootstrap\n\nfirst",
        "--output-format",
        "stream-json",
    ]
    assert invocations[1] == [
        "--session",
        "session_fake_1",
        "--skills-dir",
        str(tmp_path / "kimi-home" / "skills"),
        "-p",
        "second",
        "--output-format",
        "stream-json",
    ]
