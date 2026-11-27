# Multi-Agent Home Isolation and Daemon Ownership

Two managed Hermes agents launch under the same OS user with separate private homes, rendezvous lock directories, workspaces, and daemons. Stopping one agent terminates only its own daemon while the second agent continues working. Independently starting a daemon inside the first agent's recorded managed home causes Houmao to adopt that exact process identity on relaunch and stop it cleanly, while a daemon launched for a separate foreign home remains outside managed control.

## Sub-cases

- `m1-dual-agent-isolation`: two concurrent Hermes agents (`agent-a` and `agent-b`) bind distinct `HERMES_HOME`, `HERMES_GATEWAY_LOCK_DIR`, daemon PIDs, and `instance_id`s, and run independent workspace tasks without cross-talk.
- `m2-scoped-stop-preserves-peer`: stopping `agent-a` terminates `agent-a`'s verified daemon PID while `agent-b`'s daemon PID stays alive and completes a follow-up turn.
- `m3-same-home-daemon-adoption`: starting `hermes gateway run --external-supervisor` independently inside `agent-a`'s recorded `HERMES_HOME` causes `agent-a` relaunch to adopt that exact PID and stop it cleanly via managed `stop`.
- `m4-negative-foreign-home-untouched`: a separately started Hermes daemon in an unrelated third home (`foreign-home`) is never adopted, contacted, or stopped by `agent-a` or `agent-b` lifecycle operations.

## How to get to it (user POV)

- The operator launches two Hermes `service` agents into separate fixture run roots under `$RUN_TMP/runtime/`, inspects both managed homes with `hermes_lab.py inspect-home`, stops `agent-a`, verifies `agent-b` remains live, starts a same-home daemon in `agent-a`'s home plus a foreign-home daemon in a separate scratch home, relaunches `agent-a`, and verifies exact PID adoption and scoped cleanup.

## Driving it with hermes_lab

Preconditions:

- `fixture.py check --pool-slot a --mode service --surface manager --live` and `--pool-slot b` both exit `0`.
- `CASE_EVIDENCE="$EVIDENCE/multi-agent-isolation-and-daemon-ownership"` exists (`mkdir -p "$CASE_EVIDENCE"`).

- **Prepare and launch `agent-a` and `agent-b` (`m1`).**

```bash
pixi run python "$FIXTURE" prepare \
  --pool-slot a --mode service --surface manager \
  --prompt-mode unattended --tmux-server new --reasoning-level 5 \
  --role hermes-a --system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md" \
  --run-root "$RUN_TMP/runtime/runs-iso-a" > "$CASE_EVIDENCE/a-prepare.json"
export RUN_ISO_A="$(jq -er '.run_dir' "$CASE_EVIDENCE/a-prepare.json")"

pixi run python "$FIXTURE" prepare \
  --pool-slot b --mode service --surface manager \
  --prompt-mode unattended --tmux-server new --reasoning-level 5 \
  --role hermes-b --system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md" \
  --run-root "$RUN_TMP/runtime/runs-iso-b" > "$CASE_EVIDENCE/b-prepare.json"
export RUN_ISO_B="$(jq -er '.run_dir' "$CASE_EVIDENCE/b-prepare.json")"

pixi run python "$FIXTURE" launch --run-dir "$RUN_ISO_A" > "$CASE_EVIDENCE/a-launch.json"
pixi run python "$FIXTURE" launch --run-dir "$RUN_ISO_B" > "$CASE_EVIDENCE/b-launch.json"
pixi run python "$LAB" doctor --run-dir "$RUN_ISO_A" --run-dir "$RUN_ISO_B" --expected-effort xhigh \
  > "$CASE_EVIDENCE/doctor.json"

pixi run python "$FIXTURE" prompt --run-dir "$RUN_ISO_A" \
  --prompt "Write alpha-anchor to whoami.txt in your workspace and reply with alpha-anchor." \
  > "$CASE_EVIDENCE/a-turn1.json"
pixi run python "$FIXTURE" prompt --run-dir "$RUN_ISO_B" \
  --prompt "Write beta-anchor to whoami.txt in your workspace and reply with beta-anchor." \
  > "$CASE_EVIDENCE/b-turn1.json"

pixi run python "$LAB" inspect-home --run-dir "$RUN_ISO_A" > "$CASE_EVIDENCE/a-home-before.json"
pixi run python "$LAB" inspect-home --run-dir "$RUN_ISO_B" > "$CASE_EVIDENCE/b-home-before.json"
```

- **Stop `agent-a` and verify `agent-b` stays unaffected (`m2`).**

```bash
export PID_A_1="$(jq -er '.daemons[-1].pid' "$CASE_EVIDENCE/a-home-before.json")"
export PID_B_1="$(jq -er '.daemons[-1].pid' "$CASE_EVIDENCE/b-home-before.json")"
export HOME_A="$(jq -er '.managed_home' "$CASE_EVIDENCE/a-home-before.json")"
export SID_A="$(jq -er '.acp_bindings[-1].native_session_id' "$CASE_EVIDENCE/a-home-before.json")"

pixi run python "$LAB" stop --run-dir "$RUN_ISO_A" --evidence-root "$EVIDENCE" \
  > "$CASE_EVIDENCE/a-stop-1.json"
pixi run python "$FIXTURE" prompt --run-dir "$RUN_ISO_B" \
  --prompt "Read whoami.txt in your workspace and confirm its contents in one line." \
  > "$CASE_EVIDENCE/b-turn2-after-a-stop.json"
pixi run python "$LAB" inspect-home --run-dir "$RUN_ISO_B" > "$CASE_EVIDENCE/b-home-after-a-stop.json"
```

- **Start an independent same-home daemon in `HOME_A` plus a foreign-home daemon (`m3`, `m4`).** Use the exact `HERMES_MANAGED_API_KEY` from `private-env.json` only inside the child process environment (never print it):

```bash
export FOREIGN_HOME="$RUN_TMP/runtime/foreign-hermes-home"
mkdir -p "$FOREIGN_HOME" && chmod 700 "$FOREIGN_HOME"
cp "$HOME_A/config.yaml" "$FOREIGN_HOME/config.yaml"
cp "$HOME_A/SOUL.md" "$FOREIGN_HOME/SOUL.md"

python3 - "$RUN_ISO_A" "$HOME_A" "$FOREIGN_HOME" "$CASE_EVIDENCE/external-daemons.json" <<'PY'
import json, os, shutil, subprocess, sys, time
from pathlib import Path

run_a, home_a, foreign_home, out_path = [Path(p) for p in sys.argv[1:5]]
priv = json.loads((run_a / "private-env.json").read_text(encoding="utf-8"))
hermes = shutil.which("hermes")
assert hermes

def start_daemon(home: Path, log_name: str) -> int:
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": os.environ.get("HOME", ""),
        "HERMES_HOME": str(home),
        "HERMES_GATEWAY_LOCK_DIR": str(home / ".houmao-gateway-locks"),
        "HERMES_MANAGED_API_KEY": priv["HERMES_MANAGED_API_KEY"],
    }
    log_file = (home / log_name).open("ab")
    proc = subprocess.Popen(
        [hermes, "gateway", "run", "--external-supervisor"],
        cwd=str(run_a / "workdir"),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=log_file,
        stderr=log_file,
        start_new_session=True,
    )
    return proc.pid

pid_same = start_daemon(home_a, "adopted-test.log")
pid_foreign = start_daemon(foreign_home, "foreign-test.log")
deadline = time.monotonic() + 30
while time.monotonic() < deadline:
    if (home_a / "gateway.sock").exists() or (home_a / "gateway.sock.path").exists():
        if (foreign_home / "gateway.sock").exists() or (foreign_home / "gateway.sock.path").exists():
            break
    time.sleep(0.2)
Path(out_path).write_text(
    json.dumps({"same_home_pid": pid_same, "foreign_home_pid": pid_foreign}, indent=2) + "\n",
    encoding="utf-8",
)
PY

export ADOPTED_PID="$(jq -er '.same_home_pid' "$CASE_EVIDENCE/external-daemons.json")"
export FOREIGN_PID="$(jq -er '.foreign_home_pid' "$CASE_EVIDENCE/external-daemons.json")"
```

- **Relaunch `agent-a`, verify exact PID adoption, then stop `agent-a` and verify `FOREIGN_PID` is untouched (`m3`, `m4`).**

```bash
pixi run python "$LAB" manager --run-dir "$RUN_ISO_A" -- \
  relaunch --chat-session-mode exact --chat-session-id "$SID_A" \
  > "$CASE_EVIDENCE/a-relaunch-adopt.json"
pixi run python "$LAB" inspect-home --run-dir "$RUN_ISO_A" > "$CASE_EVIDENCE/a-home-adopted.json"
pixi run python "$FIXTURE" prompt --run-dir "$RUN_ISO_A" \
  --prompt "Read whoami.txt and confirm the anchor word." \
  > "$CASE_EVIDENCE/a-turn2-adopted.json"

pixi run python "$LAB" stop --run-dir "$RUN_ISO_A" --run-dir "$RUN_ISO_B" --evidence-root "$EVIDENCE" \
  > "$CASE_EVIDENCE/stop.json"

kill -0 "$ADOPTED_PID" 2>/dev/null && echo "adopted_alive=true" || echo "adopted_alive=false" > "$CASE_EVIDENCE/post-stop-pids.txt"
kill -0 "$FOREIGN_PID" 2>/dev/null && echo "foreign_alive_before_manual_clean=true" >> "$CASE_EVIDENCE/post-stop-pids.txt" || echo "foreign_alive_before_manual_clean=false" >> "$CASE_EVIDENCE/post-stop-pids.txt"
kill -TERM "$FOREIGN_PID" 2>/dev/null || true
```

## Expected Outcome

- **Quantified checks:**
  - `a-home-before.json` and `b-home-before.json` have disjoint `managed_home`, disjoint `daemons[-1].pid` (`PID_A_1 != PID_B_1`), and disjoint `daemons[-1].instance_id`.
  - `$RUN_ISO_A/workdir/whoami.txt` contains `alpha-anchor` and `$RUN_ISO_B/workdir/whoami.txt` contains `beta-anchor` with zero cross-contamination.
  - `a-stop-1.json` reports `surviving_daemon_pids == []`; `b-home-after-a-stop.json` retains `daemons[-1].pid == PID_B_1` (`pid_alive == true`) and `b-turn2-after-a-stop.json` succeeds.
  - `a-home-adopted.json` records `daemons[-1].pid == ADOPTED_PID` (exact adoption of the pre-started same-home daemon) and `a-turn2-adopted.json` completes.
  - `post-stop-pids.txt` confirms `adopted_alive=false` and `foreign_alive_before_manual_clean=true` (Houmao stopped the adopted same-home daemon and left the foreign-home daemon completely untouched), before our test teardown cleanly sends `SIGTERM` to `FOREIGN_PID`.
- **Qualitative checks:**
  - Inspect `b-turn2-after-a-stop.json` and `a-turn2-adopted.json` to confirm each agent reports only its own workspace anchor (`beta-anchor` vs. `alpha-anchor`) with coherent session continuity.

## Gotchas

- Always record `FOREIGN_PID` in `external-daemons.json` and terminate it with `kill -TERM "$FOREIGN_PID"` at the end of the scenario (even on failure) so no orphan daemon survives in `$RUN_TMP/runtime/foreign-hermes-home`.
- Wait for both `gateway.sock` (or `gateway.sock.path`) files to appear before running `relaunch` so the pre-started daemon has finished listening.

## Blinding and Transcript Checks

- Keep `eval`, `test`, `judge`, `rubric`, `benchmark`, `candidate`, and `arena` out of prompts and workspace files.
- Verify daemon ownership from `hermes-daemon.json`, `/proc/<pid>`, and `whoami.txt` rather than agent self-reports.
