"""Exercise external fixture launch identities and tmux env with harmless clients."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest


def test_fixture_refuses_raw_kimi_web_before_preparing_run(tmp_path: Path) -> None:
    """The fixture requires managed ownership before creating a Kimi Web run."""

    helper = Path(__file__).resolve().parents[3] / "scripts/agents/test-fixtures/fixture.py"
    run_root = tmp_path / "runs"
    result = subprocess.run(
        [
            sys.executable,
            str(helper),
            "prepare",
            "--case",
            "self-hosted",
            "--client",
            "kimi",
            "--mode",
            "web",
            "--surface",
            "raw",
            "--model",
            "Qwen/Qwen3.8-27B-FP8",
            "--base-url",
            "http://127.0.0.1:14888/v1",
            "--context-window",
            "262144",
            "--run-root",
            str(run_root),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 2, result.stderr
    error = json.loads(result.stderr)["error"]
    assert "Kimi Web fixtures require the manager surface" in error
    assert not result.stdout
    assert not run_root.exists()


@pytest.mark.parametrize("client", ["claude", "codex", "kimi"])
@pytest.mark.parametrize("case", ["self-hosted", "cloud-api"])
@pytest.mark.parametrize("surface", ["raw", "manager"])
@pytest.mark.parametrize("mode", ["tui", "headless"])
def test_tui_fixture_launch_preserves_selected_env_and_scoped_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client: str,
    case: str,
    surface: str,
    mode: str,
) -> None:
    """Real tmux children receive selected credentials despite server inheritance."""

    if shutil.which("tmux") is None:
        pytest.skip("tmux is required for this integration suite")
    repo = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repo / "scripts/agents/test-fixtures"))
    config_module = importlib.import_module("fixturelib.config")
    prepare = importlib.import_module("fixturelib.prepare")
    launch = importlib.import_module("fixturelib.launch")
    from houmao.agents.realm_controller.backends import local_interactive

    def wait_for_stub(self, **_kwargs):
        """Use the harmless child's handshake in place of vendor process names."""

        output = self._plan.working_directory / "effective-env.json"
        deadline = time.monotonic() + 5
        while not output.is_file() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert output.is_file(), "The harmless provider process did not start"

    monkeypatch.setattr(
        local_interactive.LocalInteractiveSession, "_wait_for_provider_tui", wait_for_stub
    )
    socket_root = tmp_path / "tmux-socket"
    socket_root.mkdir(mode=0o700)
    monkeypatch.setenv("TMUX_TMPDIR", str(socket_root))
    monkeypatch.delenv("TMUX", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "competing-parent-key")
    subprocess.run(["tmux", "new-session", "-d", "-s", "test-sentinel"], check=True)
    subprocess.run(
        ["tmux", "set-environment", "-g", "ANTHROPIC_API_KEY", "competing-server-key"], check=True
    )
    executable = tmp_path / "harmless-client"
    version = {"claude": "2.1.323", "codex": "0.167.2", "kimi": "2.6.0"}[client]
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys, time\n"
        f"if '--version' in sys.argv: print({version!r}); sys.exit(0)\n"
        "keys=('OPENAI_API_KEY','ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN',"
        "'KIMI_MODEL_API_KEY','OPENAI_BASE_URL','ANTHROPIC_BASE_URL','KIMI_MODEL_BASE_URL')\n"
        "pathlib.Path('effective-env.json').write_text(json.dumps({k:os.getenv(k) for k in keys}))\n"
        "if '--json' in sys.argv or '--output-format' in sys.argv:\n"
        " print(json.dumps({'session_id':'controlled-session','type':'thread.started','thread_id':'controlled-session'})); sys.exit(0)\n"
        "time.sleep(120)\n"
    )
    executable.chmod(0o700)
    prefix = "HOUMAO_TEST_SELF_HOSTED" if case == "self-hosted" else "HOUMAO_TEST_CLOUD"
    env = {f"{prefix}_MODEL": "explicit-fixture-model", f"{prefix}_CONTEXT_WINDOW": "32768"}
    if case == "cloud-api":
        env.update(
            DEEPSEEK_API_KEY="synthetic-fixture-key",
            DEEPSEEK_BASE_URL_OPENAI="https://cloud.example/v1",
            DEEPSEEK_BASE_URL_ANTHROPIC="https://cloud.example/anthropic",
        )
    else:
        env.update(
            HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL="http://localhost:19001/v1",
            HOUMAO_TEST_SELF_HOSTED_ANTHROPIC_BASE_URL="http://localhost:19001",
        )
    root = None
    try:
        config = config_module.resolve_config(
            case=case, client=client, mode=mode, surface=surface, process_env=env
        )
        run = prepare.prepare_run(config, run_root=tmp_path / "runs", executable=str(executable))
        root = Path(run["run_dir"])
        result = launch.launch_run(
            root, prompt="controlled" if mode == "headless" and surface == "raw" else None
        )
        if surface == "manager":
            assert result["identity"]["agent_id"] not in {None, "unknown"}
            manifest = Path(result["identity"]["manifest_path"])
            assert manifest.is_relative_to(root) and manifest.is_file()
            assert "synthetic-fixture-key" not in manifest.read_text()
            if mode == "headless":
                # Headless birth is idle until a separately submitted turn.
                assert launch.stop_run(root)["status"] == "stopped"
                return
        deadline = time.monotonic() + 10
        output = Path(run["workdir"]) / "effective-env.json"
        while not output.is_file() and time.monotonic() < deadline:
            time.sleep(0.05)
        child = json.loads(output.read_text())
        key = {
            "claude": "ANTHROPIC_AUTH_TOKEN",
            "codex": "OPENAI_API_KEY",
            "kimi": "KIMI_MODEL_API_KEY",
        }[client]
        assert child[key] == config.api_key.get_secret_value()
        assert "competing-server-key" not in child.values()
        assert "competing-parent-key" not in child.values()
        endpoint = {
            "claude": "ANTHROPIC_BASE_URL",
            "codex": "OPENAI_BASE_URL",
            "kimi": "KIMI_MODEL_BASE_URL",
        }[client]
        assert child[endpoint] == config.base_url
        assert launch.stop_run(root)["status"] == "stopped"
        assert (
            subprocess.run(
                ["tmux", "has-session", "-t", "test-sentinel"], capture_output=True
            ).returncode
            == 0
        )
    finally:
        if root is not None:
            launch.stop_run(root)
        subprocess.run(["tmux", "kill-server"], capture_output=True)
