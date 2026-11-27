# TUI Native Structured Control, Durable Receipts, and Ink Detachment

An operator launches a managed Hermes TUI agent (`hermes_tui`), exposing the real Hermes Ink interface in an isolated tmux pane while Houmao controls readiness, submission, receipts, and cancellation strictly through authenticated native RPC. The scenario verifies valid durable admission receipts, busy refusal, human-turn queued admission tracking, Ink detachment without losing native settlement, session-switch reporting, and explicit refusal of parser-specific TUI commands.

## Sub-cases

- `t1-attached-structured-turn`: initial state reports `terminal_attachment == "attached"`, `owner_available == true`, and `can_accept_prompt_now == true`; a managed prompt completes with a durable `hermes-native-admission.json` satisfying all strict receipt fields (`native_admission_id`, `native_admission_sequence > 0`, `native_authority_epoch > 0`, `native_execution_generation > 0`, `status == "completed"`, `native_outcome == "completed"`) and a verified workspace side effect.
- `t2-busy-refusal-and-human-turn`: while a turn is active, a second managed prompt is refused before dispatch; when a human submits input directly in the isolated Ink pane, Houmao observes activity without terminal scraping and preserves distinct native admissions when managed work is queued or submitted afterward.
- `t3-ink-detach-preserves-settlement`: closing the isolated Ink tmux pane during an admitted managed turn flips `terminal_attachment` to `"detached"` while `owner_available` remains `true` and the original admission reaches `completed`.
- `t4-negative-parser-ops-and-session-switch`: parser-specific commands (`gateway tui history` and `gateway send-keys`) explicitly report unsupported while structured native control stays available; switching Ink to a different conversation (after relaunching Ink) reports `terminal_attachment == "other_session"` while Houmao stays pinned to the original `native_session_id`.

## How to get to it (user POV)

- The operator prepares and launches a managed Hermes TUI agent with `fixture.py prepare --mode tui --surface manager --tmux-server new --reasoning-level 5` and `fixture.py launch`.
- The operator inspects structured native state via `hermes_lab.py state`, drives managed prompts via `fixture.py prompt`, interacts directly with the owned isolated tmux pane via `tmux -S "$TMUX_SOCKET"`, and verifies durable admission receipts via `hermes_lab.py inspect-home`.

## Driving it with hermes_lab

Preconditions:

- `fixture.py check --pool-slot a --mode tui --surface manager --live` exits `0`.
- `CASE_EVIDENCE="$EVIDENCE/tui-native-control-and-detachment"` exists (`mkdir -p "$CASE_EVIDENCE"`).

- **Prepare, launch, and verify attached readiness (`t1`).**

```bash
pixi run python "$FIXTURE" prepare \
  --pool-slot a --mode tui --surface manager \
  --prompt-mode unattended --tmux-server new \
  --reasoning-level 5 --role hermes-tui \
  --system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md" \
  --run-root "$RUN_TMP/runtime/runs-tui" > "$CASE_EVIDENCE/prepare.json"
export RUN_TUI="$(jq -er '.run_dir' "$CASE_EVIDENCE/prepare.json")"

pixi run python "$FIXTURE" launch --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/launch.json"
for _ in $(seq 1 30); do
  pixi run python "$LAB" state --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/state-initial.json"
  if jq -e '.state.control | .terminal_attachment == "attached" and .can_accept_prompt_now == true' "$CASE_EVIDENCE/state-initial.json" >/dev/null; then
    break
  fi
  sleep 1
done
pixi run python "$LAB" doctor --run-dir "$RUN_TUI" --expected-effort xhigh \
  > "$CASE_EVIDENCE/doctor.json"

export TUI_SOCKET="$(jq -er '.tmux_socket_path' "$RUN_TUI/run.json")"
export TUI_SESSION="$(jq -er '.state.identity.tmux_session_name' "$CASE_EVIDENCE/state-initial.json")"
export TUI_NATIVE_SID="$(jq -er '.state.control.native_session_id' "$CASE_EVIDENCE/state-initial.json")"
jq -e '.state.control | .terminal_attachment == "attached" and .owner_available and .connection_ready and .can_accept_prompt_now' \
  "$CASE_EVIDENCE/state-initial.json" >/dev/null
```

- **Run turn 1 through native RPC and inspect durable receipt (`t1`).**

```bash
pixi run python "$FIXTURE" prompt --run-dir "$RUN_TUI" \
  --prompt "Create tui-note.txt in the workspace containing the line velvet-compass-7 and reply concisely." \
  > "$CASE_EVIDENCE/prompt-turn1.json"
pixi run python "$LAB" inspect-home --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/home-snapshot-turn1.json"
jq -e '.turns[-1].status == "completed"' "$CASE_EVIDENCE/prompt-turn1.json" >/dev/null
TUI_REQUEST="$(jq -er '.turns[-1].request_id' "$CASE_EVIDENCE/prompt-turn1.json")"
jq -e --arg request "$TUI_REQUEST" --arg sid "$TUI_NATIVE_SID" \
  'any(.tui_admissions[]; .request_id == $request and .native_session_id == $sid and
      .status == "completed" and .native_outcome == "completed" and
      (.native_admission_id | length) > 0 and .native_admission_sequence >= 1 and
      .native_authority_epoch >= 1 and .native_execution_generation >= 1)' \
  "$CASE_EVIDENCE/home-snapshot-turn1.json" >/dev/null
cp "$RUN_TUI/workdir/tui-note.txt" "$CASE_EVIDENCE/tui-note.txt"
```

- **Negative parser-specific operations (`t4`).** Verify `gateway tui history` and `gateway send-keys` report unsupported while `state` remains healthy:

```bash
pixi run python "$LAB" manager --run-dir "$RUN_TUI" --allow-error -- gateway tui history \
  > "$CASE_EVIDENCE/negative-parser-history.json"
pixi run python "$LAB" manager --run-dir "$RUN_TUI" --allow-error -- gateway send-keys --text "hello" \
  > "$CASE_EVIDENCE/negative-send-keys.json"
pixi run python "$LAB" state --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/state-after-parser-negatives.json"
```

- **Busy refusal and direct human Ink input (`t2`).** Trigger a bounded human turn in the isolated Ink pane (`sleep 25` shell command), poll until native activity is active (`can_accept_prompt_now == false`), attempt a managed prompt (confirming busy refusal), then wait for idle and confirm the managed conversation remains intact:

```bash
env -u TMUX -u TMUX_PANE tmux -S "$TUI_SOCKET" send-keys -t "$TUI_SESSION" -l \
  "Run a shell command that sleeps 20 seconds and writes human-done to human.txt."
sleep 0.5
env -u TMUX -u TMUX_PANE tmux -S "$TUI_SOCKET" send-keys -t "$TUI_SESSION" Enter

for _ in $(seq 1 30); do
  pixi run python "$LAB" state --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/state-during-human.json"
  if jq -e '.state.control.can_accept_prompt_now == false' "$CASE_EVIDENCE/state-during-human.json" >/dev/null; then
    break
  fi
  sleep 1
done

pixi run python "$LAB" manager --run-dir "$RUN_TUI" --allow-error -- \
  prompt --prompt "Second managed turn while busy." \
  > "$CASE_EVIDENCE/busy-refusal.json"
jq -e '.ok == false' "$CASE_EVIDENCE/busy-refusal.json" >/dev/null

for _ in $(seq 1 90); do
  pixi run python "$LAB" state --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/state-after-human.json"
  if jq -e '.state.control.can_accept_prompt_now == true' "$CASE_EVIDENCE/state-after-human.json" >/dev/null; then
    break
  fi
  sleep 2
done
test -f "$RUN_TUI/workdir/human.txt" && cp "$RUN_TUI/workdir/human.txt" "$CASE_EVIDENCE/human.txt"
```

- **Detach Ink during an admitted managed turn (`t3`).** Start a managed turn in the background, wait until its `active_request_id` / `native_admission_id` appears in `state`, kill only the isolated Ink pane session on `$TUI_SOCKET`, confirm `terminal_attachment == "detached"` while `owner_available == true`, and wait for the managed prompt to settle cleanly:

```bash
pixi run python "$FIXTURE" prompt --run-dir "$RUN_TUI" \
  --prompt "Sleep 15 seconds using the shell tool, then write detached-ok to detach-proof.txt and reply with detached-ok." \
  > "$CASE_EVIDENCE/prompt-detach.json" &
DETACH_PID=$!

for _ in $(seq 1 30); do
  pixi run python "$LAB" state --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/state-before-detach.json"
  if jq -e '.state.control | .active_request_id != null and .native_admission_id != null' "$CASE_EVIDENCE/state-before-detach.json" >/dev/null; then
    break
  fi
  sleep 1
done
DETACH_REQUEST="$(jq -er '.state.control.active_request_id' "$CASE_EVIDENCE/state-before-detach.json")"
DETACH_ADMISSION="$(jq -er '.state.control.native_admission_id' "$CASE_EVIDENCE/state-before-detach.json")"

env -u TMUX -u TMUX_PANE tmux -S "$TUI_SOCKET" kill-session -t "$TUI_SESSION"
pixi run python "$LAB" state --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/state-while-detached.json"
jq -e '.state.control | .terminal_attachment == "detached" and .owner_available' "$CASE_EVIDENCE/state-while-detached.json" >/dev/null
wait "$DETACH_PID"
pixi run python "$LAB" inspect-home --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/home-snapshot-after-detach.json"
jq -e --arg request "$DETACH_REQUEST" \
  '.turns[-1] | .request_id == $request and .status == "completed"' "$CASE_EVIDENCE/prompt-detach.json" >/dev/null
jq -e --arg request "$DETACH_REQUEST" --arg admission "$DETACH_ADMISSION" \
  'any(.tui_admissions[]; .request_id == $request and .native_admission_id == $admission and .native_outcome == "completed")' \
  "$CASE_EVIDENCE/home-snapshot-after-detach.json" >/dev/null
cp "$RUN_TUI/workdir/detach-proof.txt" "$CASE_EVIDENCE/detach-proof.txt"
```

- **Exact relaunch of Ink and session-switch check (`t4`).** Relaunch Ink on `$TUI_NATIVE_SID`, send `/new` in Ink to switch the UI view to a different conversation, verify `terminal_attachment == "other_session"` while `native_session_id` remains `$TUI_NATIVE_SID`, and confirm one follow-up managed prompt still recalls `velvet-compass-7`:

```bash
pixi run python "$LAB" manager --run-dir "$RUN_TUI" -- \
  relaunch --chat-session-mode exact --chat-session-id "$TUI_NATIVE_SID" \
  > "$CASE_EVIDENCE/relaunch-exact.json"
for _ in $(seq 1 30); do
  pixi run python "$LAB" state --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/state-after-relaunch.json"
  if jq -e '.state.control.terminal_attachment == "attached"' "$CASE_EVIDENCE/state-after-relaunch.json" >/dev/null; then
    break
  fi
  sleep 1
done
export TUI_SESSION_AFTER="$(jq -er '.state.identity.tmux_session_name' "$CASE_EVIDENCE/state-after-relaunch.json")"
env -u TMUX -u TMUX_PANE tmux -S "$TUI_SOCKET" send-keys -t "$TUI_SESSION_AFTER" -l "/new"
sleep 0.5
env -u TMUX -u TMUX_PANE tmux -S "$TUI_SOCKET" send-keys -t "$TUI_SESSION_AFTER" Enter
for _ in $(seq 1 20); do
  if env -u TMUX -u TMUX_PANE tmux -S "$TUI_SOCKET" capture-pane -p -t "$TUI_SESSION_AFTER" \
    | rg -q 'Start a new session\?'; then
    env -u TMUX -u TMUX_PANE tmux -S "$TUI_SOCKET" send-keys -t "$TUI_SESSION_AFTER" y
    break
  fi
  sleep 0.5
done
for _ in $(seq 1 20); do
  pixi run python "$LAB" state --run-dir "$RUN_TUI" > "$CASE_EVIDENCE/state-after-switch.json"
  if jq -e '.state.control.terminal_attachment == "other_session"' "$CASE_EVIDENCE/state-after-switch.json" >/dev/null; then
    break
  fi
  sleep 1
done
jq -e --arg sid "$TUI_NATIVE_SID" \
  '.state.control | .terminal_attachment == "other_session" and .native_session_id == $sid' \
  "$CASE_EVIDENCE/state-after-switch.json" >/dev/null

pixi run python "$FIXTURE" prompt --run-dir "$RUN_TUI" \
  --prompt "Write the phrase from our earlier conversation to recall.txt and reply in one line." \
  > "$CASE_EVIDENCE/prompt-pinned-after-switch.json"
cp "$RUN_TUI/workdir/recall.txt" "$CASE_EVIDENCE/recall.txt"
```

- **Cross-check and proof.**

```bash
pixi run python "$LAB" capture-transcript --run-dir "$RUN_TUI" --output "$CASE_EVIDENCE/transcript" \
  > "$CASE_EVIDENCE/capture.json"
pixi run python "$LAB" audit-redaction --run-dir "$RUN_TUI" "$CASE_EVIDENCE" \
  > "$CASE_EVIDENCE/redaction-audit.json"
pixi run python "$LAB" stop --run-dir "$RUN_TUI" --evidence-root "$EVIDENCE" \
  > "$CASE_EVIDENCE/stop.json"
```

## Expected Outcome

- **Quantified checks:**
  - Native readiness is in `.state.control`. When the Houmao gateway is attached, `.gateway.observation` gives a second view. The fixture reports the request ID and outcome in `.turns`.
  - `state-initial.json` reports `terminal_attachment == "attached"`, `owner_available == true`, `connection_ready == true`, and `can_accept_prompt_now == true`.
  - `home-snapshot-turn1.json` records a `tui_admissions` entry with non-empty `native_admission_id`, `native_admission_sequence >= 1`, `native_authority_epoch >= 1`, `native_execution_generation >= 1`, `status == "completed"`, and `native_outcome == "completed"`; `tui-note.txt` contains `velvet-compass-7`.
  - `negative-parser-history.json` and `negative-send-keys.json` both return unsupported errors (`ok == false`), while `state-after-parser-negatives.json` retains `owner_available == true`.
  - `state-during-human.json` reports `can_accept_prompt_now == false`; `busy-refusal.json` returns an explicit refusal (`ok == false`) without dispatching a second prompt.
  - `state-while-detached.json` reports `terminal_attachment == "detached"` and `owner_available == true`; `prompt-detach.json` settles with completed status and `detach-proof.txt` contains `detached-ok`.
  - `state-after-switch.json` reports `terminal_attachment == "other_session"` while `native_session_id == "$TUI_NATIVE_SID"`; `redaction-audit.json` has `leak_count == 0`; `stop.json` has `surviving_daemon_pids == []`.
- **Qualitative checks:**
  - Match the request ID in `prompt-pinned-after-switch.json` to the native admission in `transcript/` and confirm it used the original session ID. Confirm `recall.txt` contains `velvet-compass-7`.

## Gotchas

- Ink writes its active-session hint file asynchronously after startup; always poll `state` until `terminal_attachment == "attached"` instead of using a fixed sleep.
- Never target the caller's ambient tmux server; every `tmux` command must explicitly pass `-S "$TUI_SOCKET"` with `env -u TMUX -u TMUX_PANE`.
- If the human turn finishes before the busy refusal runs, increase the shell sleep duration slightly (e.g., 30s) rather than skipping the busy check.

## Blinding and Transcript Checks

- Keep `eval`, `test`, `judge`, `rubric`, `benchmark`, `candidate`, and `arena` out of Ink inputs, managed prompts, and workspace files.
- Confirm durable state from `tui-note.txt`, `detach-proof.txt`, and `hermes-native-admission.json` records rather than assistant summaries alone.
