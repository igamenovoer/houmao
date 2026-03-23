## Context

The scripted Claude Code state-tracking harness already proves the simplified model against captured tmux sessions, but it is optimized for batch scenarios and post-run comparison. Developers still need an operator-facing interactive workflow, similar in spirit to the existing dual shadow-watch demo, where they can:

- launch a real Claude Code tmux session from a generated brain home,
- attach and prompt Claude manually,
- watch the simplified state model change live on a dashboard, and
- stop the run with replay-grade artifacts and a final pass/fail-style analysis report.

This interactive watch must remain outside `houmao-server`. It should reuse the existing explore-harness capture model, versioned detector selection, and ReactiveX-timed reducer rather than introducing a second state model.

Constraints:

- the Claude session should be launched from repository brain fixtures under `tests/fixtures/agents/brains/`, using a generated runtime home and its `launch.sh`,
- the generated runtime home should live under the interactive run's own output root so each run is self-contained and inspectable,
- the launch path must support API-key and third-party endpoint backed Claude setups through fixture-managed config and credential profiles rather than a hard-coded wrapper command,
- the interactive watch should not depend on `houmao-server` routes or shell out to Houmao session lifecycle CLIs for build/start/stop; it should use shared Python/library code and direct tmux/recorder orchestration instead,
- live observation must stay aligned with authoritative recorder/runtime artifacts rather than becoming a separate ad hoc poller,
- timed behavior must stay ReactiveX-driven,
- interactive prompting is manual, so the watch cannot assume authoritative prompt-submission markers, and
- debugging must rely on recorded evidence and optional dense harness-local traces, not guesswork.

## Goals / Non-Goals

**Goals:**

- Add an interactive watch workflow under `scripts/explore/claude-code-state-tracking/`.
- Start a real tmux-backed Claude session plus a live dashboard that shows simplified state transitions as the operator interacts.
- Launch Claude through a fresh brain home built from `tests/fixtures/agents/brains/` recipes, config profiles, and credential profiles.
- Keep the watch implementation as independent as practical from `houmao-server` and Houmao lifecycle CLIs.
- Reuse the same detector family and Rx reducer semantics as the scripted explore harness.
- Persist live state samples, state transitions, inspectable metadata, and replay-grade recorder/runtime artifacts.
- Finalize each interactive run with offline groundtruth, replay, comparison, and a developer-readable report.
- Make mismatches debuggable through retained artifacts and optional dense local trace streams.

**Non-Goals:**

- Replacing `houmao-server` or its demos.
- Adding multi-agent or multi-pane watch support in the first pass.
- Inferring manual prompt submission with stronger semantics than the simplified visible-signal model already supports.
- Turning the interactive watch into a CI-required path.

## Decisions

### 1. The interactive watch will be a separate pack layered on top of the explore harness artifacts

The new workflow will be a companion pack under `scripts/explore/claude-code-state-tracking/` rather than another mode embedded invisibly inside the current `run` command.

It will provide an operator-friendly command surface similar to the existing shadow-watch demo:

- `start`
- `inspect`
- `stop`

`start` launches the interactive Claude tmux session, recorder, runtime observer, and dashboard. `inspect` exposes the current state and attach points. `stop` shuts down the watch and finalizes analysis artifacts.

Rationale:

- The batch harness and the interactive watch serve different operator needs.
- A separate pack makes the interactive workflow discoverable and keeps the batch harness scripts focused on automated scenarios.
- The existing shadow-watch demo proved the value of start/inspect/stop ergonomics and explicit attach commands.

Alternative considered: add `--interactive` flags to the batch harness CLI. Rejected because it would mix two different operating modes into one command surface and make the operator workflow harder to discover.

### 2. Claude launch will come from fixture-built brain homes rather than `claude-yunwu`

The interactive watch will not hard-code `claude-yunwu` as its launch command. Instead it will:

- select a Claude brain recipe under `tests/fixtures/agents/brains/brain-recipes/claude/`,
- build a fresh runtime home from the recipe, config profile, and credential profile using the repository brain workflow, and
- launch the generated `launch.sh` inside tmux.

This keeps the interactive watch aligned with the repository's reusable brain-fixture system and allows API-key plus third-party endpoint backed Claude launches through fixture-managed credentials and config rather than through a bespoke wrapper command.

Rationale:

- The repository already has a brain-first launch workflow for Claude.
- Brain recipes and credential profiles are the source-of-truth for reproducible tool setup in this workspace.
- This avoids overfitting the interactive watch to one wrapper command and makes launch configuration switchable through fixture inputs.

Alternative considered: continue using `claude-yunwu` because it is already present in the batch harness. Rejected because the repository brain fixtures already provide a more general launch contract and the design should not be tied to that wrapper.

### 3. Brain construction will use shared Python builder APIs, not Houmao CLI shellouts

The interactive watch may reuse Houmao library modules such as the brain builder, recorder service, tmux helpers, and detector/reducer code, but it should not invoke Houmao session-management CLIs as subprocesses for its normal workflow.

In particular, the watch should:

- build the Claude brain home through shared Python APIs such as `build_brain_home`,
- launch the resulting `launch.sh` directly in tmux,
- manage recorder lifecycle through the recorder service APIs, and
- manage run lifecycle through its own driver code.

It should not depend on:

- `houmao-server`,
- `houmao-cli`,
- `houmao.agents.realm_controller build-brain`,
- `start-session`, `send-prompt`, or `stop-session` subprocess calls.

Rationale:

- This is an explore workflow, not a thin wrapper over the managed-session system.
- Avoiding CLI shellouts reduces coupling to unrelated runtime/session-management behavior.
- It keeps the watch focused on the state-model question while still allowing reuse of stable shared modules.

Alternative considered: call existing Houmao CLIs as subprocesses because they already exist. Rejected because that would make the watch depend on more Houmao lifecycle behavior than necessary and weaken its value as an independent validation tool.

### 4. Brain runtime homes will be created under the interactive run root

Each interactive run will own its generated brain runtime and manifest paths under a run-local subtree instead of writing into a shared global runtime location.

The intended layout is:

```text
tmp/explore/claude-code-state-tracking/<run-id>/
├── runtime/
│   ├── homes/<home-id>/
│   │   └── launch.sh
│   └── manifests/<home-id>.yaml
├── workdir/
├── artifacts/
├── analysis/
└── terminal-record-.../
```

`start` should return the run root together with the concrete runtime paths so the operator can inspect or remove the run as a single unit.

Rationale:

- Interactive runs should be isolated from one another.
- The generated brain home is part of the run evidence and should live beside the other retained artifacts.
- This avoids accidental reuse of stale global runtime state across interactive runs.

Alternative considered: reuse the shared default runtime root that the brain builder can target. Rejected because it weakens run isolation and makes cleanup and artifact inspection harder.

### 5. The dashboard will consume the same recorded observation stream that later drives offline analysis

The interactive watch will still start the terminal recorder in `passive` mode and the existing runtime observer loop. The dashboard will not independently sample tmux as its primary state source. Instead, it will tail the same appended observation artifacts that the offline analysis uses:

- recorder `pane_snapshots.ndjson`
- harness `runtime_observations.ndjson`

The live dashboard loop will read new appended observations, run detector selection plus the live Rx reducer, and persist:

- `state_samples.ndjson`
- `transitions.ndjson`
- `latest_state.json`

Rationale:

- This keeps live display, offline replay, and later debugging anchored to the same raw evidence.
- It avoids subtle disagreement between “what the dashboard saw” and “what the recorder captured”.
- It matches the spirit of the server-backed shadow-watch demo, where the monitor consumes a shared authoritative state source instead of inventing its own parsing contract.

Alternative considered: have the dashboard capture tmux directly while the recorder runs separately. Rejected because it would introduce avoidable sampling skew and make post-run mismatch analysis harder.

### 6. Live state reduction will reuse the same detector family and ReactiveX reducer semantics as replay

The live dashboard must not invent a second interpretation path. The interactive watch will factor the existing replay logic into a reusable stream-driven reducer so both live watch and offline replay share:

- closest-compatible detector selection,
- `ready | active | unknown` turn phase semantics,
- `success | interrupted | known_failure | none` terminal outcome semantics,
- settle timing, invalidation, and reset behavior driven by ReactiveX.

The live watch will feed appended observations into that reducer incrementally. Offline replay will continue to feed recorded observations under a scheduler.

Rationale:

- The interactive watch is supposed to validate and visualize the same state model, not a cousin of it.
- Sharing the reducer keeps the live dashboard honest and prevents model drift.
- The recent truncated-footer bug demonstrated that detector and reducer behavior need to be fixable in one place.

Alternative considered: keep a separate lightweight live reducer just for the dashboard. Rejected because it would create two semantics surfaces to maintain and debug.

### 7. The dashboard will present simplified user-facing state, signal notes, and diagnostics rather than raw parser internals

The live dashboard will render the simplified public state model rather than the older lifecycle-heavy server model. At minimum it will show:

- diagnostics availability
- turn phase
- last terminal result
- accepting-input / editing-input / ready-posture surface facts
- active reasons
- detector notes such as interruption or known-failure signal matches
- observed version and detector family
- sample id / elapsed time

It will use colored text for the primary state tokens so the operator can scan transitions quickly.

Rationale:

- The point of this workflow is to validate the simplified model in action.
- Showing raw internal bookkeeping would obscure the operator-facing question of whether state transitions look correct.
- Colored state tokens already improved readability in the existing dashboard work.

Alternative considered: render only the raw latest pane text and separate JSON state. Rejected because it would not satisfy the “watch for state change as interaction goes” goal.

### 8. `inspect` and final reports will make the run debuggable without attaching a debugger first

The interactive pack will persist enough metadata that a developer can reason from artifacts after the fact.

`inspect --json` will expose at minimum:

- run root
- run-local runtime root
- brain home path
- brain manifest path
- Claude tmux attach command
- dashboard attach command
- recorder root
- latest state payload
- paths to `state_samples.ndjson`, `transitions.ndjson`, and final analysis artifacts when available

`stop` will trigger offline finalization:

- groundtruth classification
- replay classification
- comparison report
- an interactive-run report under the interactive watch root explaining whether the run passed or failed semantically

Rationale:

- The operator should not need to reconstruct paths manually after an interactive session.
- The earlier live-run report pattern is already useful and should become part of the pack rather than an ad hoc afterthought.

Alternative considered: keep only recorder artifacts and ask developers to run replay/compare manually. Rejected because it adds friction and makes the interactive pack less self-contained.

### 9. The first pass will watch one Claude tmux session and one dashboard session

The initial interactive watch will manage one Claude session and one dashboard session. This keeps the live workflow aligned with the current single-session Claude harness and avoids premature complexity around multi-pane coordination.

Rationale:

- The current explore harness is Claude-specific and single-session.
- One dashboard is enough to validate live state transitions for the first pass.
- Multi-session coordination can be added later once the single-session watch proves stable.

Alternative considered: immediately support two or more concurrent interactive Claude sessions. Rejected because it increases process/session management complexity without changing the core state-model question.

### 10. Debugging support will be env-gated and artifact-first

When live interactive behavior looks wrong, the first debugging path must remain artifact inspection:

- raw pane snapshots
- runtime liveness observations
- live `state_samples.ndjson`
- live `transitions.ndjson`
- final groundtruth/replay/comparison artifacts

If that is insufficient, the pack may enable an env-gated dense trace mode that writes local detector/reducer streams such as:

- `detector_signals.ndjson`
- `rx_events.ndjson`
- `dashboard_render_events.ndjson`

The trace mode must be local to the interactive watch pack and must not be required for normal operation.

Rationale:

- We want concrete evidence before changing detection logic.
- The existing harness debugging pattern already showed that retained artifacts usually identify the issue without a debugger.
- Optional dense trace is still valuable when a live mismatch cannot be explained from retained artifacts alone.

Alternative considered: always emit dense logs. Rejected because it adds noise and overhead to routine interactive runs.

## Risks / Trade-offs

- [Live dashboard lags appended recorder samples] → Keep the dashboard driven by small polling intervals over appended observation files and surface sample ids/timestamps so lag is visible.
- [Shared reducer refactor introduces regression in batch replay] → Add focused tests around the extracted reducer and rerun the existing explore harness unit coverage.
- [Manual prompting does not reliably produce all interesting state paths] → Preserve artifacts and reports so the operator can rerun targeted prompts instead of guessing from memory.
- [Known-failure paths remain hard to reproduce interactively] → Keep the interactive watch useful for ready/active/interrupted/success/process-loss paths first, and treat failure generation as a separate scenario-generation problem.

## Migration Plan

1. Factor the current replay tracker into a shared stream-driven reducer that both replay and live watch can use.
2. Add the brain-home build and launch flow from `tests/fixtures/agents/brains/` using shared Python builder APIs, plus the interactive watch driver, dashboard process, run manifest, and inspect/stop workflow under `scripts/explore/claude-code-state-tracking/`.
3. Add live state artifact persistence (`latest_state.json`, `state_samples.ndjson`, `transitions.ndjson`) and finalization report generation.
4. Validate the new pack against at least one successful interactive run and one interrupted run.
5. If needed, enable the env-gated trace mode only for debugging mismatches during validation.

Rollback is straightforward because this change is additive: remove the interactive pack entrypoints and shared live-watch wiring while keeping the existing batch harness intact.

## Open Questions

- Should the first interactive pack include an operator command to add human labels/notes during the run, or is artifact-first post-run analysis enough for now?
- Should the dashboard show a compact diff/transition history inline, or keep the main screen focused on current state and leave history to `transitions.ndjson` plus the report?
