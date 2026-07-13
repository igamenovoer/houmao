## Why

UC-02 now defines 101 exact Boltons operations, but Houmao does not yet have one reproducible qualification workflow that executes the required Codex, Claude, and Kimi session matrix and keeps copied projects, recordings, labels, replay sweeps, and reports under a single owned run root. Without that workflow, long-horizon results remain difficult to reproduce, compare, resume after manual labeling, or use as a release gate.

## What Changes

- Add an executable long-horizon TUI-tracking qualification workflow for the provider/procedure matrix defined by UC-02: Claude on ST-01 through ST-04, Codex on ST-01 through ST-05, and Kimi on ST-03 through ST-05.
- Materialize each provider/procedure attempt from the pinned vendored Boltons fixture, create a run-local baseline repository, expand the exact UC-02 prompts and control actions, and launch every provider in its maintained unattended posture.
- Require one caller-selected or generated run root under `tmp/<subdir>/`; copied projects, isolated provider homes, recordings, labels, replay variants, project diffs, logs, failure slices, and aggregate reports SHALL remain beneath that root.
- Split execution into resumable preflight, capture, manual-label, replay, and aggregate-report phases so tracker output cannot influence human ground truth.
- Reuse the maintained terminal recorder and shared TUI tracking replay paths for approximately 20 fps canonical capture and 10 Hz, 5 Hz, 2 Hz, phase-offset, and available irregular-cadence validation.
- Enforce provider-specific readiness gates, including Codex proxy projection through port 7990, unattended confirmation rejection, exact navigation/exit action probes, fixture immutability, and declared mutation scopes.
- Produce separate engineering-task and tracker verdicts, preserving `scenario_task_divergence`, `stimulus_too_short`, unsupported-surface, confirmation-policy, and tracker-invariant failures without conflating them.
- Add hermetic tests for planning, path ownership, prompt expansion, matrix completeness, resume behavior, artifact schemas, and replay/report aggregation; keep live provider execution in explicit manual/integration qualification commands.
- Gemini CLI is outside the provider matrix and SHALL receive no scenario, launch, credential, or report support.

## Capabilities

### New Capabilities

- `long-horizon-tui-tracking-qualification`: Defines the UC-02 provider matrix, owned `tmp/<subdir>` run layout, Boltons project preparation, exact-operation execution, manual-label boundary, replay sweeps, verdict separation, resume semantics, and aggregate acceptance report.

### Modified Capabilities

None.

## Impact

- Affects the shared TUI tracking demo/qualification tooling, terminal recording and replay orchestration, scenario definitions, manual/integration tests, and developer documentation.
- Reads the vendored fixture at `tests/fixtures/test-projects/boltons` and local credential fixtures, while treating both as immutable inputs.
- Creates potentially large and credential-adjacent runtime artifacts only below the selected `tmp/<subdir>` root; secrets remain excluded from manifests and reports.
- Uses the existing maintained Claude, Codex, and Kimi launch-policy strategies and detector profiles; it does not change public runtime APIs or add provider compatibility shims.
