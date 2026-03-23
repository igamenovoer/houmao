# Interactive Watch Live Validation 2026-03-20

## Scope

Validate the `add-claude-code-state-tracking-interactive-watch` workflow against a real tmux-backed Claude Code session launched from repo brain fixtures, then explain the problems found during live bring-up and why the final run passed or failed.

## Problems Found

1. The dashboard tmux launcher exited immediately because the generated helper script used `exec cd ... && ...` instead of execing a shell command correctly.
2. The generated Claude `launch.sh` reparsed quoted `.env` values in shell and preserved the quotes in the child process environment, which caused `API Error: Invalid URL` from quoted `ANTHROPIC_BASE_URL`.
3. The live reducer cleared `last_turn_result=success` when a later active turn started, but the state-model design says `last_turn` is sticky until a later terminal outcome supersedes it.
4. The Claude 2.1.80 detector allowed `success_candidate` too early on a ready surface that still carried the yellow installer/advisory footer, so replay settled success before the final stable ready surface actually arrived.

## Fixes Applied

1. Fixed the dashboard launcher to exec `bash -lc "<command>"`.
2. Changed brain-home launch helper generation to export parsed allowlisted env vars directly at build time instead of reparsing the `.env` file in shell.
3. Kept `last_turn_result` sticky across a later `turn_phase=active` observation.
4. Added a Claude 2.1.x ready-footer advisory rule so the installer notice blocks `success_candidate` until the footer collapses back to the benign ready footer.

The newly formalized signal note is:

- `openspec/changes/simplify-houmao-server-state-model/tui-signals/claude-code-ready-footer-advisory.md`

## Final Validated Run

- Run root: `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/interactive-watch/validate-success-live`
- Brain home: `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/interactive-watch/validate-success-live/runtime/homes/claude-brain-20260320-075826Z-8e3651`
- Final comparison: `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/interactive-watch/validate-success-live/analysis/comparison.json`
- Final watch report: `/data1/huangzhe/code/houmao/tmp/explore/claude-code-state-tracking/interactive-watch/validate-success-live/analysis/interactive_watch_report.md`

Important validated boundaries:

- First manual turn:
  - active detected at `s000345`
  - success candidate begins only after the advisory footer clears
  - settled success at `s000502`
- Second manual turn:
  - active detected at `s000697`
  - interrupted terminal result at `s000791`

## Verdict

Passed.

Reason:

- the interactive watch started from a run-local brain home built from fixtures
- the Claude process received the correct unquoted `ANTHROPIC_*` env vars
- live inspect showed the expected simplified state changes during manual prompting
- offline groundtruth and replay comparison finished with `mismatch_count=0` and `transition_order_matches=true`
