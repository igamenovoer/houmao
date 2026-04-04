from __future__ import annotations

from pathlib import Path


_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_RUNNER_PATH = _WORKSPACE_ROOT / "scripts/demo/minimal-agent-launch/scripts/run_demo.sh"
_TUTORIAL_PATH = _WORKSPACE_ROOT / "scripts/demo/minimal-agent-launch/tut-agent-launch-minimal.md"


def test_runner_uses_one_overlay_override_without_legacy_root_overrides() -> None:
    script_text = _RUNNER_PATH.read_text(encoding="utf-8")

    assert 'overlay_root="${workdir}/.houmao"' in script_text
    assert "unset HOUMAO_AGENT_DEF_DIR HOUMAO_GLOBAL_RUNTIME_DIR" in script_text
    assert 'export HOUMAO_PROJECT_OVERLAY_DIR="${overlay_root}"' in script_text
    assert "export HOUMAO_AGENT_DEF_DIR" not in script_text
    assert "export HOUMAO_GLOBAL_RUNTIME_DIR" not in script_text


def test_tutorial_documents_overlay_local_runtime_and_jobs_layout() -> None:
    tutorial_text = _TUTORIAL_PATH.read_text(encoding="utf-8")

    assert 'overlay_root="${run_root}/workdir/.houmao"' in tutorial_text
    assert "unset HOUMAO_AGENT_DEF_DIR HOUMAO_GLOBAL_RUNTIME_DIR" in tutorial_text
    assert 'HOUMAO_PROJECT_OVERLAY_DIR="$PWD/${overlay_root}" \\' in tutorial_text
    assert "HOUMAO_AGENT_DEF_DIR=" not in tutorial_text
    assert "HOUMAO_GLOBAL_RUNTIME_DIR=" not in tutorial_text
    assert "`workdir/.houmao/runtime/`" in tutorial_text
    assert "`workdir/.houmao/jobs/`" in tutorial_text
