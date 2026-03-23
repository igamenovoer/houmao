## 1. Preserve Launch Intent And Surface Stable Evidence

- [x] 1.1 Update the mail ping-pong demo brain-build path to pass the tracked recipe `operator_prompt_mode` into `BuildRequest`.
- [x] 1.2 Extend demo inspect/report generation so each role records tracked recipe mode, built brain manifest mode, live launch request mode, and whether launch policy was applied.
- [x] 1.3 Update sanitization and any tracked expected report artifacts so the new launch posture summary remains snapshot-stable.
- [x] 1.4 Ensure the launched headless participants keep rolling CLI output visible in their tmux panes during active turns, without reintroducing tmux-based lifecycle inference.

## 2. Define The Canonical HTT Case Before Implementation

- [x] 2.1 Add `openspec/changes/preserve-mail-ping-pong-operator-prompt-mode/testplans/case-unattended-full-run.md` covering the canonical automatic and interactive variants for the unattended full-run path.
- [x] 2.2 Keep the design, spec delta, and testplan aligned on the same implementation root: `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/`.

## 3. Add Pack-Local Automatic And Interactive HTT Surfaces

- [x] 3.1 Add the standalone harness `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/run-case.sh` for case selection and shared preflight orchestration.
- [x] 3.2 Add the automatic case `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/case-unattended-full-run.sh` that runs `start -> launch-posture-check -> kickoff -> wait -> inspect -> verify -> stop`.
- [x] 3.3 Add the independent interactive guide `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/case-unattended-full-run.md`.
- [x] 3.4 Add shared helper scripts under `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/helpers/` for preflight, output-root handling, launch-posture checks, tmux attach hints or pane snapshots, and result writing.

## 4. Fail Fast, Preserve Artifacts, And Verify

- [x] 4.1 Add HTT preflight checks for required commands, tracked fixture files, and tracked credential/config roots so missing prerequisites fail before `run_demo.sh start`.
- [x] 4.2 Make the automatic case stop or clean stale demo-owned state under the selected output root before a new run, while preserving artifacts from the current attempt on failure.
- [x] 4.3 Emit a machine-readable case result under `<output-root>/control/autotest/` and ensure failure paths return non-zero without deleting useful artifacts.
- [x] 4.4 Preserve bounded tmux watch diagnostics for failed post-launch runs so operators can inspect what was visible in the pane.
- [x] 4.5 Extend deterministic pytest coverage for launch posture summaries and the new artifact contract, and run the focused demo-pack test suite plus the canonical automatic case when local prerequisites are available.
