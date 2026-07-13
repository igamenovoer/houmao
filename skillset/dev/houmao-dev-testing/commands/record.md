# Record a Tmux Test Session

## Workflow

1. **Resolve inputs and create a fresh run root.** Require a provider, task or use-case description, test project, expected operations, stop condition, and `tmp/<subdir>` output location.
2. **Translate the description into an executable operation plan.** Preserve exact prompts, control keys, fixed holds, direct visible-pattern waits, and expected observable outcomes in `definitions/`.
3. **Preflight the provider and project.** Require Claude, Codex, or Kimi; unattended mode; local credentials; tmux; asciinema; and the Codex proxy when applicable.
4. **Launch a normal TUI and begin a 20 Hz active recording before the first operation.** Follow **Capture Paths**.
5. **Drive every operation and retain its timing and outcome.** Do not query Houmao state tracking to decide when the recorded agent is ready or active.
6. **Stop, freeze, and audit the recording.** Record taints, failures, hashes, provider version, and incomplete operations without deleting partial evidence.

If the task needs actions the maintained scenario driver cannot express, use the native planning tool to build a tracker-blind tmux driving plan with the same inputs, recorder, timing log, and freeze requirements, then execute it.

## Required Inputs

- Provider: `claude`, `codex`, or `kimi`
- Exact task or use-case description
- Test project path or instructions for making an isolated copy under the run root
- Ordered user operations, including prompts and control keys
- Observable completion condition for each operation
- Run root, defaulting to `tmp/houmao-dev-testing/<UTC timestamp>-<provider>-<case>`

Do not begin from a vague goal when exact interactions affect state coverage. Convert the goal into a versioned `definitions/task.md` and, for automated driving, `definitions/scenario.json`.

## Tracker-Blind Operation Plan

The canonical recording must not use the current detector as an oracle. In scenario JSON, use:

- `send_text` and `send_key` for exact input
- `wait_seconds` for planned holds that must remain observable
- `wait_for_pattern` only for a direct, documented TUI surface pattern
- `interrupt_turn`, `close_tool`, or a process/session stop when the use case explicitly requires it

Do not use `wait_for_ready`, `wait_for_active`, `wait_for_interrupted_signal`, or `wait_for_interrupted_ready` for canonical blind evidence. The maintained driver implements those actions with the detector under test.

Each step needs a unique name. Store expected meaning separately from the raw pattern so later UI wording changes remain visible instead of silently redefining the test.

## Capture Paths

### Scenario-Driven Launch

Prefer the maintained shared TUI tracking demo when the task fits its action vocabulary. Write the scenario under the run root, keep the capture output path absent, then run:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-capture \
  --scenario "<run-root>/definitions/scenario.json" \
  --output-root "<run-root>/capture" \
  --profile high_rate_authoring \
  --sample-interval-seconds 0.05 \
  --json
```

The driver launches a normal provider TUI in unattended mode, records managed input and runtime evidence, and writes `drive_events.ndjson`. Verify the resolved recipe and prompt mode in the captured manifests.

### Existing Tmux Session

When the agent has already been launched by a different supported workflow, discover its exact pane and use the generic recorder:

```bash
pixi run python -m tools.terminal_record start \
  --mode active \
  --target-session "<tmux-session>" \
  --target-pane "<pane-id>" \
  --tool "<provider>" \
  --run-root "<run-root>/capture/recording" \
  --sample-interval-seconds 0.05
```

Use the recorder-owned attach path or Houmao-managed `send-keys` so input events remain attributable. Stop explicitly with `tools.terminal_record stop` after the final settled hold.

## Unattended and Provider Rules

- Use prompt mode `unattended` for every provider.
- A confirmation UI is a test failure or explicit upstream exception, not a routine operator step.
- For Codex, export `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY` and their lowercase equivalents with `http://127.0.0.1:7990` before preflight and launch.
- Use the repository's maintained local auth bundle defaults. Never copy secret values into task definitions, manifests, logs, or reports.
- Do not add Gemini CLI cases.

## Freeze Gate

Before `label` or `replay`:

1. Confirm recorder status is `stopped` and `manifest.json` has `stopped_at_utc` plus `stop_reason`.
2. Confirm `pane_snapshots.ndjson` and `input_events.ndjson` exist; require runtime observations when the scenario includes TUI/process loss.
3. Record SHA-256 digests for the recorder manifest, source snapshots, input events, runtime observations, scenario, and operation log in `<run-root>/capture/frozen-evidence.json`.
4. Record `run_tainted` and every taint reason. Do not turn a tainted capture into a clean pass.
5. Make retries in a new run root or numbered attempt.

## Outputs

- `definitions/task.md`
- optional `definitions/scenario.json`
- `capture/recording/manifest.json`
- `capture/recording/pane_snapshots.ndjson`
- `capture/recording/input_events.ndjson`
- `capture/runtime_observations.ndjson` and `capture/drive_events.ndjson` when scenario-driven
- `capture/frozen-evidence.json`
- capture status in `report.md`
