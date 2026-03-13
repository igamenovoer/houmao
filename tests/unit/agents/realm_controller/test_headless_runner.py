from __future__ import annotations

from pathlib import Path

from houmao.agents.realm_controller.backends.headless_runner import (
    HeadlessCliRunner,
)


def test_headless_runner_parses_stream_json_and_session_id(tmp_path: Path) -> None:
    script = tmp_path / "emit_stream.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        'echo \'{"type":"delta","text":"hello"}\'\n'
        'echo \'{"type":"final","session_id":"sess-123","text":"done"}\'\n',
        encoding="utf-8",
    )
    script.chmod(0o755)

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="stream-json",
    )

    assert result.returncode == 0
    assert result.session_id == "sess-123"
    assert [event.kind for event in result.events] == ["delta", "final"]


def test_headless_runner_parses_json_payload(tmp_path: Path) -> None:
    script = tmp_path / "emit_json.sh"
    script.write_text(
        '#!/usr/bin/env bash\necho \'{"type":"result","session_id":"sess-999","text":"ok"}\'\n',
        encoding="utf-8",
    )
    script.chmod(0o755)

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="json",
    )

    assert result.returncode == 0
    assert result.session_id == "sess-999"
    assert len(result.events) == 1
    assert result.events[0].message == "ok"


def test_headless_runner_extracts_codex_thread_id_from_stream_json(
    tmp_path: Path,
) -> None:
    script = tmp_path / "emit_codex_jsonl.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        'echo \'{"type":"thread.started","thread_id":"thread-abc"}\'\n'
        'echo \'{"type":"response.completed","text":"done"}\'\n',
        encoding="utf-8",
    )
    script.chmod(0o755)

    runner = HeadlessCliRunner()
    result = runner.run(
        command=[str(script)],
        env={},
        cwd=tmp_path,
        turn_index=1,
        output_format="stream-json",
    )

    assert result.returncode == 0
    assert result.session_id == "thread-abc"
