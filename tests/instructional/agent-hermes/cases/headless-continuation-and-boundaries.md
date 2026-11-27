# Headless Continuation, Literal Input, and Preflight Boundaries

An operator runs a managed Hermes agent in `headless` mode (`hermes chat --oneshot --query-file - --format stream-json`), verifying that finite per-turn CLI processes continue one verified logical session across distinct worker PIDs, pass multiline text and shell metacharacters literally via private stdin, preserve continuity across exact relaunch, refuse unattributable headless interrupts and `latest` continuation, and fail cleanly when `hermes` is missing from `PATH`.

## Sub-cases

- `h1-multi-turn-finite-workers`: two turns execute in separate finite CLI processes while reusing one verified logical `session_id`, preserving `agent.reasoning_effort: xhigh` and writing separate `stdout.jsonl` and `stderr.log` turn artifacts.
- `h2-multiline-metacharacter-stdin`: turn 2 supplies multiline input containing `$()`, backticks, single/double quotes, and `$HOME` literally through stdin, and the agent persists the exact literal string into a workspace file without shell expansion while recalling turn-1 context.
- `h3-exact-relaunch-turn3`: exact relaunch with the recorded `session_id` completes turn 3 in the same conversation and workspace.
- `h4-negative-interrupt-latest-and-unprepared-owner`: Headless `interrupt` and `relaunch --chat-session-mode tool_last_or_new` return explicit refusals. Preparing against an unprepared test owner leaves the current profile intact.

## How to get to it (user POV)

- The operator prepares and launches a managed Hermes headless agent with `fixture.py prepare --mode headless --surface manager --reasoning-level 5` and `fixture.py launch`.
- The operator submits turns with `fixture.py prompt`, inspects per-turn `hermes-request.json` and `stdout.jsonl`/`stderr.log` via `hermes_lab.py inspect-home`, exercises exact relaunch and negative controls via `hermes_lab.py manager`, and verifies missing-`PATH` preflight in a subshell with a minimal `PATH`.

## Driving it with hermes_lab

Preconditions:

- `fixture.py check --pool-slot a --mode headless --surface manager --live` exits `0`.
- `CASE_EVIDENCE="$EVIDENCE/headless-continuation-and-boundaries"` exists (`mkdir -p "$CASE_EVIDENCE"`).

- **Prepare and launch managed headless (`h1`).**

```bash
pixi run python "$FIXTURE" prepare \
  --pool-slot a --mode headless --surface manager \
  --prompt-mode unattended --tmux-server new \
  --reasoning-level 5 --role hermes-hl \
  --system-prompt-file "$BUNDLE_ROOT/helpers/roles/hermes-worker.md" \
  --run-root "$RUN_TMP/runtime/runs-headless" > "$CASE_EVIDENCE/prepare.json"
export RUN_HL="$(jq -er '.run_dir' "$CASE_EVIDENCE/prepare.json")"

pixi run python "$FIXTURE" launch --run-dir "$RUN_HL" > "$CASE_EVIDENCE/launch.json"
pixi run python "$LAB" doctor --run-dir "$RUN_HL" --expected-effort xhigh \
  > "$CASE_EVIDENCE/doctor.json"
```

- **Turn 1 and Turn 2 with literal multiline/metacharacter input (`h1`, `h2`).**

```bash
pixi run python "$FIXTURE" prompt --run-dir "$RUN_HL" \
  --prompt "Remember the project tag quartz-ridge-42. Create notes.txt in the workspace containing the single line quartz-ridge-42 and confirm." \
  > "$CASE_EVIDENCE/prompt-turn1.json"

MULTILINE_PROMPT=$'Recall the project tag from our first turn.\nWrite a file named literal.txt containing these exact two lines without expanding variables or commands:\nline1: $(echo NOT_EXPANDED) `uname` "$HOME"\nline2: quartz-ridge-42'
pixi run python "$FIXTURE" prompt --run-dir "$RUN_HL" --prompt "$MULTILINE_PROMPT" \
  > "$CASE_EVIDENCE/prompt-turn2.json"

pixi run python "$LAB" inspect-home --run-dir "$RUN_HL" > "$CASE_EVIDENCE/home-snapshot-after-turn2.json"
cp "$RUN_HL/workdir/literal.txt" "$CASE_EVIDENCE/literal.txt"
```

- **Negative controls: headless interrupt refusal, `tool_last_or_new` rejection, and missing `PATH` (`h4`).**

```bash
export HL_SID="$(jq -er '.headless_turns[-1].session_id' "$CASE_EVIDENCE/home-snapshot-after-turn2.json")"
BEFORE_HASH="$(find "$(jq -er '.managed_home' "$CASE_EVIDENCE/home-snapshot-after-turn2.json")" -maxdepth 2 -type f -exec sha256sum {} + | sort)"

pixi run python "$LAB" manager --run-dir "$RUN_HL" --allow-error -- interrupt \
  > "$CASE_EVIDENCE/negative-interrupt.json"

pixi run python "$LAB" manager --run-dir "$RUN_HL" --allow-error -- \
  relaunch --chat-session-mode tool_last_or_new \
  > "$CASE_EVIDENCE/negative-tool-last.json"

pixi run python "$FIXTURE" prepare \
  --pool-slot a --mode headless --surface manager --tmux-server new \
  --hermes-owner-root "$RUN_TMP/unprepared-owner" --run-root "$RUN_TMP/runtime/neg-no-hermes" \
  > "$CASE_EVIDENCE/negative-unprepared-owner.txt" 2>&1 || echo "unprepared_owner_exit=$?" > "$CASE_EVIDENCE/negative-unprepared-owner-exit.txt"

AFTER_HASH="$(find "$(jq -er '.managed_home' "$CASE_EVIDENCE/home-snapshot-after-turn2.json")" -maxdepth 2 -type f -exec sha256sum {} + | sort)"
test "$BEFORE_HASH" = "$AFTER_HASH" && echo "home_unchanged=true" > "$CASE_EVIDENCE/negative-home-integrity.txt"
```

- **Exact relaunch and Turn 3 (`h3`).**

```bash
pixi run python "$LAB" manager --run-dir "$RUN_HL" -- \
  relaunch --chat-session-mode exact --chat-session-id "$HL_SID" \
  > "$CASE_EVIDENCE/relaunch-exact.json"

pixi run python "$FIXTURE" prompt --run-dir "$RUN_HL" \
  --prompt "What project tag did we record in turn 1, and what file did you write in turn 2? Reply in one concise line." \
  > "$CASE_EVIDENCE/prompt-turn3.json"

pixi run python "$LAB" inspect-home --run-dir "$RUN_HL" > "$CASE_EVIDENCE/home-snapshot-final.json"
```

- **Cross-check and proof.**

```bash
pixi run python "$LAB" capture-transcript --run-dir "$RUN_HL" --output "$CASE_EVIDENCE/transcript" \
  > "$CASE_EVIDENCE/capture.json"
pixi run python "$LAB" audit-redaction --run-dir "$RUN_HL" "$CASE_EVIDENCE" \
  > "$CASE_EVIDENCE/redaction-audit.json"
pixi run python "$LAB" stop --run-dir "$RUN_HL" --evidence-root "$EVIDENCE" \
  > "$CASE_EVIDENCE/stop.json"
```

## Expected Outcome

- **Quantified checks:**
  - `prepare.json` reports `backend == "hermes_headless"`; `doctor.json` confirms `agent.reasoning_effort == "xhigh"` on the managed launch home.
  - `home-snapshot-final.json` records `len(headless_turns) == 3`, with identical non-empty `session_id` across all three turns, `turn_index` strictly `1, 2, 3`, `exitcode == 0`, `stdout_exists == true`, `stderr_exists == true`, and `result_frame.exit_code == 0` with `result_frame.session_id == "$HL_SID"` and `result_frame.error` falsy.
  - `literal.txt` contains the verbatim substring `$(echo NOT_EXPANDED) ` `` `uname` `` `"$HOME"` (zero shell expansion of `$HOME` or `uname`) plus `quartz-ridge-42`.
  - `negative-interrupt.json` reports refusal/error (`ok == false` or `status == "error"`) stating an attributable native admission is required, and does not alter `session_id`.
  - `negative-tool-last.json` reports refusal. The unprepared owner returns a nonzero exit and an owner preparation diagnostic. `negative-home-integrity.txt` confirms `home_unchanged=true`.
  - `redaction-audit.json` exits `0` (`leak_count == 0`). `stop.json` records `profile_parked == true`.
- **Qualitative checks:**
  - Inspect `prompt-turn2.json`, `prompt-turn3.json`, and `transcript/runtime-artifacts/*/stdout.jsonl` to confirm genuine multi-turn recall of `quartz-ridge-42` and `literal.txt` across separate finite processes and exact relaunch.

## Gotchas

- Choose an unused scratch path for the unprepared-owner check.
- Each headless turn has a 300-second dispatch deadline; keep prompts focused so `xhigh` thinking completes comfortably within that window.

## Blinding and Transcript Checks

- Keep `eval`, `test`, `judge`, `rubric`, `benchmark`, `candidate`, and `arena` out of prompts and workspace filenames.
- Verify turn continuation and output from `literal.txt`, `hermes-request.json`, and captured `stdout.jsonl` frames, not solely from assistant text.
