"""Launch claude under tmux through the OpenLux relay launcher lane.

Implements the claude campaign's launch contract (iteration 1 plan,
credential/cost lane): session 1 runs the user's
``~/.local/bin/claude-openlux-0.5x`` wrapper as-is (it appends
``--dangerously-skip-permissions``); session 2 replicates the wrapper's
environment lane in-shell but omits the bypass flag so approval surfaces
render. Both lanes pass ``--model sonnet`` (user directive 2026-10-12:
the relay bills real money). The OpenLux key file is never read by this
process — the pane shell performs the command substitution, exactly as
the wrapper script does.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from houmao.agents.realm_controller.backends.tmux_runtime import run_tmux

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_LAUNCHER = Path.home() / ".local/bin" / "claude-openlux-0.5x"
DEFAULT_KEY_FILE = Path.home() / ".local/bin" / "openlux-api-key"
DEFAULT_MODEL = "sonnet"
PANE_WIDTH = 220
PANE_HEIGHT = 50

_SURFACE_MARKERS = (
    "Quick safety check",  # trust dialog (untrusted workdir, both postures)
    "for shortcuts",  # settled composer footer
    "bypass permissions on",  # unattended composer footer
    "Do you want to proceed",  # approval surface (defensive)
)

_NO_BYPASS_ENV_LANE = (
    'export ANTHROPIC_AUTH_TOKEN="$(tr -d \'[:space:]\' < "$HOME/.local/bin/openlux-api-key")"; '
    'export ANTHROPIC_BASE_URL="https://api.openlux.ai"; '
    "unset ANTHROPIC_API_KEY CLAUDE_CODE_OAUTH_TOKEN; "
    'export API_TIMEOUT_MS="${API_TIMEOUT_MS:-300000}"; '
    'export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="${CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS:-1}"; '
    'export CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY="${CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY:-1}"; '
    "unset ANTHROPIC_MODEL ANTHROPIC_DEFAULT_OPUS_MODEL ANTHROPIC_DEFAULT_SONNET_MODEL "
    "ANTHROPIC_DEFAULT_HAIKU_MODEL ANTHROPIC_DEFAULT_FABLE_MODEL CLAUDE_CODE_SUBAGENT_MODEL; "
)


def launch_claude(
    *,
    run_root: Path,
    workdir: Path,
    session_name: str,
    posture: str,
    model: str = DEFAULT_MODEL,
    timeout_seconds: float = 120.0,
) -> dict[str, Any]:
    """Launch one claude TUI in detached tmux and write launch metadata.

    Parameters
    ----------
    run_root:
        Fresh campaign run root; launch artifacts land in ``launch/``.
    workdir:
        Working directory for the session (trusted or deliberately untrusted).
    session_name:
        Unique tmux session name; must not already exist.
    posture:
        ``unattended`` runs the openlux launcher as-is (bypass flag baked in);
        ``as_is`` replicates the launcher's environment lane minus the bypass
        flag so approval surfaces render (documented deviation, iteration 1
        plan binding rule 1).
    model:
        Model selector passed through to claude (campaign default ``sonnet``).
    timeout_seconds:
        Bounded startup verification window.

    Returns
    -------
    dict
        Launch metadata also persisted to ``launch/launch.json``.
    """

    launch_dir = run_root / "launch"
    launch_dir.mkdir(parents=True, exist_ok=True)

    executable = shutil.which("claude")
    if executable is None:
        raise RuntimeError("`claude` does not resolve on PATH")
    version = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, timeout=30
    ).stdout.strip()
    if not DEFAULT_LAUNCHER.is_file():
        raise RuntimeError(f"OpenLux launcher missing at `{DEFAULT_LAUNCHER}`")
    if not DEFAULT_KEY_FILE.is_file():
        raise RuntimeError(f"OpenLux key file missing at `{DEFAULT_KEY_FILE}` (existence only)")

    if run_tmux(["has-session", "-t", session_name]).returncode == 0:
        raise RuntimeError(f"tmux session `{session_name}` already exists")

    if posture == "unattended":
        pane_command = f"exec {DEFAULT_LAUNCHER} --model {model}"
        launcher_description = "claude-openlux-0.5x wrapper as-is (bypass baked in)"
    elif posture == "as_is":
        pane_command = f"bash -c '{_NO_BYPASS_ENV_LANE}exec {executable} --model {model}'"
        launcher_description = (
            "openlux environment lane replicated in-shell, bypass flag omitted "
            "(iteration 1 plan deviation)"
        )
    else:
        raise RuntimeError(f"Unsupported posture: {posture!r}")

    result = run_tmux(
        [
            "new-session",
            "-d",
            "-s",
            session_name,
            "-x",
            str(PANE_WIDTH),
            "-y",
            str(PANE_HEIGHT),
            "-c",
            str(workdir),
            pane_command,
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(f"tmux new-session failed: {result.stderr.strip()}")

    pane_id = ""
    surface_text = ""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        panes = run_tmux(["list-panes", "-t", session_name, "-F", "#{pane_id}"])
        if panes.returncode == 0 and panes.stdout.strip():
            pane_id = panes.stdout.splitlines()[0].strip()
            capture = run_tmux(["capture-pane", "-p", "-t", pane_id])
            surface_text = capture.stdout if capture.returncode == 0 else ""
            if any(marker in surface_text for marker in _SURFACE_MARKERS):
                break
        time.sleep(1.0)
    else:
        raise RuntimeError(
            f"claude surface did not stabilize within {timeout_seconds}s in `{session_name}`"
        )

    pane_pid_row = run_tmux(["display-message", "-p", "-t", pane_id, "#{pane_pid}"])
    pane_pid = int(pane_pid_row.stdout.strip()) if pane_pid_row.returncode == 0 else None

    metadata: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_root.name,
        "provider": "claude",
        "provider_version": version,
        "workdir": str(workdir),
        "run_root": str(run_root),
        "tmux_session": session_name,
        "tmux_pane": pane_id,
        "pane_pid": pane_pid,
        "pane_width": PANE_WIDTH,
        "pane_height": PANE_HEIGHT,
        "launcher_command": DEFAULT_LAUNCHER.name,
        "launcher_path": str(DEFAULT_LAUNCHER),
        "launcher_sha256": _sha256(DEFAULT_LAUNCHER),
        "claude_binary_path": str(Path(executable).resolve()),
        "credential_strategy": "OpenLux relay via claude-openlux-0.5x lane (key file existence checked, never read by this process)",
        "credential_source_path": str(DEFAULT_KEY_FILE),
        "posture": posture,
        "launcher_description": launcher_description,
        "model": model,
        "provider_arguments": ["--model", model],
        "launched_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "startup_verification": "surface marker observed in bounded poll",
    }
    (launch_dir / "launch.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (launch_dir / "launch-report.md").write_text(
        "\n".join(
            [
                f"# Launch Report: {session_name}",
                "",
                f"- provider: claude {version} (`{executable}`)",
                f"- posture: {posture} ({launcher_description})",
                f"- model: {model} (relay-resolved; TUI banner verification is scenario op 0)",
                f"- workdir: `{workdir}`",
                f"- tmux: session `{session_name}`, pane `{pane_id}`, {PANE_WIDTH}x{PANE_HEIGHT}",
                f"- attach: `tmux attach-session -t {session_name}`",
                "- credential check: OpenLux key file existence verified (contents never read)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return metadata


def kill_session(*, session_name: str) -> None:
    """Tear down the campaign-owned tmux session."""

    run_tmux(["kill-session", "-t", session_name])


def _sha256(path: Path) -> str:
    """Return the SHA-256 hex digest of one file."""

    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
