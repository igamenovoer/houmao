# Record a Tmux Test Session

## Workflow

1. **Resolve inputs and create a fresh run root.** Require a provider, task or use-case description, test project, expected operations, stop condition, and `tmp/<subdir>` output location.
2. **Translate the description into an executable operation plan.** Preserve exact prompts, control keys, fixed holds, direct visible-pattern waits, and expected observable outcomes in `definitions/`.
3. **Preflight the project and recording tools.** Require Claude, Codex, or Kimi; unattended mode; tmux; and the terminal recorder. Leave provider executable, credential, launcher, and proxy resolution to `houmao-dev-launch-agents`.
4. **Delegate launch and begin a 20 Hz active recording before the first operation.** Follow **Delegated Launch and Capture**.
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

## Delegated Launch and Capture

### Launch Through `houmao-dev-launch-agents`

Select the matching skill subcommand and request unattended launch in the isolated test-project workdir:

- Claude: `$houmao-dev-launch-agents use launch-claude-code ...`
- Codex: `$houmao-dev-launch-agents use launch-codex ...`
- Kimi: `$houmao-dev-launch-agents use launch-kimi-code ...`

Pass the test-project workdir, unattended posture, a unique tmux session name, and `<run-root>/launch/` as the requested launch-artifact location. Do not reconstruct or bypass the selected provider command. Require the delegated result to identify a verified live tmux session and pane before starting the recorder. Copy or reference its non-secret launch metadata from the test report.

When the user supplies an already-running agent session, verify that it was launched through `houmao-dev-launch-agents` for this test. If its launch provenance is unavailable, launch a fresh session through that skill rather than adopting it.

### Record the Delegated Tmux Session

Use the exact session and pane returned by the launch skill:

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

The shared TUI demo's `recorded-capture` command owns provider launch, so do not invoke it from this skill. Use its tracker-blind scenario action vocabulary as planning guidance, then drive the delegated pane through recorder-owned or Houmao-managed input surfaces. If a future maintained interface accepts an externally launched session, it may replace the run-local driver without changing launch ownership.

## Unattended and Provider Rules

- Use prompt mode `unattended` for every provider.
- A confirmation UI is a test failure or explicit upstream exception, not a routine operator step.
- Let `houmao-dev-launch-agents` resolve provider credentials, launchers, and Codex proxy settings. Never copy secret values into task definitions, manifests, logs, or reports.
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
- `launch/launch.json` and `launch/launch-report.md`, or an explicit reference to the delegated launch artifacts
- `capture/recording/manifest.json`
- `capture/recording/pane_snapshots.ndjson`
- `capture/recording/input_events.ndjson`
- `capture/runtime_observations.ndjson` and `capture/drive_events.ndjson` when scenario-driven
- `capture/frozen-evidence.json`
- capture status in `report.md`
