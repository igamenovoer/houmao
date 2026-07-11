# Interfaces

## Scope

This document defines the interfaces that `houmao-dev-testing` must teach or coordinate. It covers the conversational skill contract, provider matrix, maintained command surfaces, evidence files, label independence, replay schedules, validation modes, verdicts, errors, and persistence rules.

The design does not add a second Houmao lifecycle CLI. The skill composes existing `houmao-mgr`, terminal-recorder, and shared TUI tracking demo commands. One planned extension is explicit: deterministic irregular-cadence stream derivation is not present in the current CLI.

## Covered Use Cases

- `UC-01`: Validate Agent Launches and Runtime Behavior

## Interfaces

### Skill Invocation Contract

Purpose: Accept a development-testing goal and guide the operator through the narrowest supported workflow.

Inputs:

- `providers`: Optional list drawn from `claude`, `codex`, and `kimi`. Default is the smallest set named by the request.
- `postures`: Optional list drawn from `tui` and `headless`.
- `scenarios`: Optional scenario identifiers such as `explicit_success`, `interrupted_after_active`, `blocking_approval`, `known_failure`, `transient_overlay`, and `tui_down_after_active`.
- `workflow`: Optional selector drawn from `preflight`, `managed_smoke`, `native_tui_capture`, `label`, `canonical_replay`, `cadence_sweep`, and `full`.
- `workdir`: Optional test work directory. It must resolve outside credential source directories.
- `output_root`: Optional retained artifact root. Default is `tmp/houmao-dev-testing/<run-id>/`.
- `capture_interval_seconds`: Optional positive number. Native TUI qualification defaults to `0.05`.
- `replay_plan`: Optional path to a replay schedule document.
- `mutation_scope`: Optional statement of resources the skill may create, stop, replace, or clean up.

Outputs:

- A resolved test matrix and preflight report before mutation.
- Commands that use `pixi run` for Python and Houmao entrypoints.
- Explicit human gates before prompting a native TUI, accepting labels, publishing fixtures, or deleting non-owned state.
- A final report with separate managed launch, headless, canonical TUI, and cadence-robustness results.

Validation:

- The skill must inspect the current checkout and `--help` output when a command surface may have changed.
- The skill must reject TUI qualification for a provider without a maintained tracker profile.
- The skill must exclude Gemini from all testing work. It must not install, configure, launch, diagnose, or qualify Gemini.
- The skill must not silently replace an unsupported matrix cell with a legacy CLI.
- The skill must distinguish resources it owns from pre-existing provider sessions and credentials.

Errors:

- `unsupported_provider_posture`: The requested provider and posture combination has no maintained path.
- `provider_out_of_scope`: The request includes Gemini or another provider outside the skill's explicit Claude, Codex, and Kimi scope.
- `missing_prerequisite`: A binary, auth bundle, tmux target, or repository asset is unavailable.
- `unsafe_mutation_scope`: The requested workflow would overwrite credentials or unrelated runtime state.
- `human_gate_required`: Recording review, label approval, or fixture publication needs operator input.

### Provider Capability Matrix

Purpose: Prevent the skill from conflating provider launch support with tracked TUI support.

| Provider | Managed TUI | Managed Headless | Native TUI Recording | TUI Replay Analysis | Default Local Auth Fixture |
| --- | --- | --- | --- | --- | --- |
| Claude Code | Supported | Supported | Supported | Supported | `tests/fixtures/auth-bundles/claude/kimi-coding/` |
| Codex | Supported | Supported | Supported | Supported | `tests/fixtures/auth-bundles/codex/yunwu-openai/` |
| Kimi Code | Supported | Supported | Supported | Supported | `tests/fixtures/auth-bundles/kimi/personal-a-default/` when locally prepared |

Validation:

- Capability resolution must come from current launch code, tracker registry, recorder choices, and repository guidance.
- Gemini is not a capability-matrix cell. Its pending removal makes Gemini testing irrelevant to this skill even while some implementation remains in the checkout.
- A missing local Kimi bundle is `missing_prerequisite`, not proof that Kimi support is absent.
- Native TUI recording support does not mean a provider has a valid tracker. Replay analysis requires a maintained profile.

Errors:

- `capability_changed`: Current code or command help contradicts the matrix. The skill must stop and report the evidence.

### Resolved Test Session Manifest

Purpose: Preserve the test intent and every resolved input before commands mutate runtime state.

Authoring example:

```yaml
schema_version: 1
run_id: codex-success-20260711T120000Z
provider: codex
postures:
  - tui
  - headless
scenario: explicit_success
workdir: /absolute/path/to/isolated-workdir
output_root: /absolute/path/to/tmp/houmao-dev-testing/codex-success-20260711T120000Z
auth:
  display_name: yunwu-openai
  source: tests/fixtures/auth-bundles/codex/yunwu-openai
native_tui:
  tmux_session: native-codex-success
  tmux_pane: "%12"
  capture_interval_seconds: 0.05
replay_plan: replay-plan.yaml
mutation_scope:
  may_create_project_overlay: true
  may_stop_owned_sessions: true
  may_modify_auth_source: false
```

Required fields:

- `schema_version`, `run_id`, `provider`, `scenario`, `output_root`, and `mutation_scope`.
- `native_tui` when the workflow records or labels a TUI.
- `replay_plan` when the workflow evaluates degraded cadence.

Validation:

- `output_root`, `workdir`, and retained artifact paths must resolve to absolute paths in the resolved manifest.
- `capture_interval_seconds` must be positive. A request for 20 fps resolves to `0.05` seconds.
- The tmux pane is required when the selected session has more than one pane.
- Credential source contents must not be copied into the manifest.

Errors:

- `invalid_manifest`: A required field, enum value, path, or numeric bound is invalid.
- `ambiguous_tmux_target`: The session has multiple panes and no exact pane was selected.

### Managed Agent Command Surface

Purpose: Exercise Houmao-owned configuration, launch, prompt, observation, and cleanup behavior through maintained entrypoints.

Baseline command sequence:

```bash
pixi run houmao-mgr project init

pixi run houmao-mgr project credentials <provider> add \
  --name <auth-display-name> \
  <provider-specific-import-options>

pixi run houmao-mgr project specialist create \
  --name <specialist> \
  --tool <provider> \
  --credential <auth-display-name> \
  --system-prompt "<bounded test role>"

pixi run houmao-mgr project profile create \
  --name <profile> \
  --specialist <specialist> \
  --agent-name <agent-name> \
  --workdir <workdir> \
  --prompt-mode unattended

pixi run houmao-mgr project agents launch --profile <profile> [--headless]
pixi run houmao-mgr agents single --agent-name <agent-name> state
pixi run houmao-mgr project agents stop --name <agent-name>
```

Rules:

- Fixture bundle paths are import sources. The skill must register a project credential before selecting it with `--credential`.
- Provider-specific import options come from current command help. Typical file-backed inputs are Claude `--config-dir <bundle>/files`, Codex `--auth-json <bundle>/files/auth.json`, and Kimi `--code-home <bundle>/files`.
- The skill must read a bundle's `env/vars.env` only through a redaction-safe import path. It must never echo secret values into command logs or reports.
- Exactly one of `--profile` and `--specialist` selects a managed launch.
- The skill defaults automated TUI tests to unattended prompt posture unless the scenario specifically tests native provider prompts.
- The skill uses unique run-scoped specialist, profile, agent, and tmux names unless the user selects existing definitions.
- Launch completion alone is insufficient. A smoke result needs prompt or turn evidence, state evidence, and cleanup evidence.

Errors:

- `managed_launch_failed`: Configuration succeeded but the managed runtime did not start.
- `runtime_not_observable`: The runtime started but scoped state or turn evidence cannot be retrieved.
- `cleanup_incomplete`: A skill-owned live process or tmux session remains after cleanup.

### Headless Test Contract

Purpose: Verify prompt submission, structured output, completion, error propagation, interruption when applicable, and retained runtime artifacts without TUI parsing.

Inputs:

- Managed agent identity.
- A bounded prompt with an observable completion condition.
- Optional model and reasoning overrides when the scenario targets those features.
- Timeout and interruption policy.

Outputs:

- Prompt or turn request result.
- Turn status and event sequence.
- Captured stdout and stderr.
- Exit or completion classification.
- Managed state before and after the turn.
- Cleanup result.

Validation:

- Headless success requires the expected output condition and a successful runtime completion state.
- A non-zero provider exit, timeout, or malformed structured stream must remain visible as a failure.
- Headless testing must not claim TUI tracker coverage.

### Independent Native TUI Capture Contract

Purpose: Create ground-truth evidence without allowing Houmao to shape provider behavior.

Preconditions:

- The provider is launched directly in a dedicated tmux session using its ordinary interactive entrypoint.
- The provider home and prompt do not contain Houmao-managed instructions, system skills, gateway state, or launch manifests.
- The operator confirms the exact tmux pane and scripted scenario before recording.

Recorder command:

```bash
pixi run python -m tools.terminal_record start \
  --mode passive \
  --target-session <native-session> \
  --target-pane <pane-id> \
  --tool <claude|codex|kimi> \
  --run-root <output-root>/native-tui/terminal-record \
  --sample-interval-seconds 0.05
```

Outputs:

- `manifest.json`: requested cadence, actual timing metadata, provider, tmux target, and recorder status.
- `session.cast`: human review surface. It is not the automated replay source.
- `pane_snapshots.ndjson`: authoritative machine replay surface.
- `input_events.ndjson`: optional evidence. Passive capture does not promise authoritative input capture.

Validation:

- The recorder must use passive mode for independent baseline capture.
- The operator must prompt the native TUI. Houmao gateway or managed send-keys paths are prohibited in this phase.
- Sample timestamps, not the requested fps label, define actual source timing.
- A source stream with long unexplained gaps must be marked insufficient for strict temporal claims.

Errors:

- `contaminated_native_baseline`: Houmao-managed state influenced the provider session.
- `capture_rate_not_sustained`: Observed source intervals materially exceed the requested interval.
- `recording_incomplete`: The run lacks a stopped manifest or authoritative pane snapshots.

### Manual Label Contract

Purpose: Preserve independent expected public tracked state for canonical replay.

Inputs:

- Source sample or inclusive sample range.
- Scenario identifier and label identifier.
- Public fields such as diagnostics availability, surface posture, turn phase, last-turn result, and last-turn source.
- Evidence notes that point to visible terminal facts or explicit scenario actions.

Command shape:

```bash
pixi run python -m tools.terminal_record add-label \
  --run-root <terminal-record-root> \
  --label-id <label> \
  --scenario-id <scenario> \
  --sample-id <start-sample> \
  [--sample-end-id <end-sample>] \
  --diagnostics-availability <value> \
  --turn-phase <value> \
  --last-turn-result <value> \
  --last-turn-source <value> \
  --evidence-note "<visible or operator-known evidence>"
```

Validation:

- Labels must cover the canonical comparison range without overlap.
- Labels target public tracked state. They must not encode detector-specific signals or temporal hints.
- Tracker output must remain hidden while labels are authored or revised.
- Explicit settle semantics belong in the label timeline. A visible answer may precede the public success transition.
- Evidence notes must support the label without including secrets.

Errors:

- `label_coverage_gap`: One or more canonical samples have no expected public state.
- `label_overlap`: More than one label range claims the same source sample.
- `circular_ground_truth`: Tracker output was used as the authority for expected labels.
- `semantic_label_error`: A label contradicts the documented public state contract.

### Canonical Replay Contract

Purpose: Determine whether the current tracker matches human-authored public-state expectations on the original source stream.

Commands:

```bash
pixi run python -m tools.terminal_record analyze \
  --run-root <terminal-record-root> \
  --tool <claude|codex|kimi>

pixi run python -m tools.terminal_record validate \
  --run-root <terminal-record-root>
```

Comparison:

- The canonical path uses the unmodified source samples and their identifiers.
- The primary result is strict sample-aligned public-state comparison.
- Ordered transition comparison is a secondary check.
- Parser and detector internals remain diagnostic evidence, not ground truth.

Outputs:

- `parser_observed.ndjson`.
- `state_observed.ndjson`.
- Machine-readable validation results.
- A strict pass or fail with sample-level mismatch evidence.

### Replay Schedule Contract

Purpose: Describe fixed and irregular observation schedules derived from one high-frequency source stream.

Authoring example:

```yaml
schema_version: 1
source: native-tui/terminal-record/pane_snapshots.ndjson
source_capture_interval_seconds: 0.05
variants:
  - id: source_20hz
    kind: source
  - id: fixed_10hz
    kind: fixed_interval
    interval_seconds: 0.1
  - id: fixed_5hz
    kind: fixed_interval
    interval_seconds: 0.2
  - id: fixed_2hz
    kind: fixed_interval
    interval_seconds: 0.5
  - id: jittered_5hz
    kind: seeded_jitter
    base_interval_seconds: 0.2
    jitter_seconds: 0.12
    seed: 7319
    max_gap_seconds: 0.5
  - id: burst_delay
    kind: interval_sequence
    intervals_seconds: [0.1, 0.1, 0.4, 0.15, 0.5, 0.2]
    repeat: true
contracts:
  strict_variant: source_20hz
  degraded_variants:
    required_sequence: [ready, active, ready_success]
    required_terminal_result: success
    forbidden_terminal_results: [known_failure]
    max_first_occurrence_drift_seconds: 2.0
```

Required fields:

- `schema_version`, `source`, at least one source variant, and at least one degraded variant.
- Stable variant identifiers.
- A deterministic `seed` for randomized schedules.
- A semantic contract for every degraded variant, directly or by shared default.

Validation:

- Derived variants may select only samples present in the source recording.
- Every derived row must retain `source_sample_id` and source timing.
- A fixed interval cannot be faster than the source evidence.
- A schedule must be deterministic across repeated runs.
- `max_gap_seconds`, when present, must be positive and no smaller than the base interval.

Errors:

- `unsupported_schedule_kind`: The installed harness cannot derive the requested schedule.
- `invalid_replay_schedule`: The schedule is non-deterministic, faster than source evidence, or violates numeric constraints.

Current compatibility boundary:

- `tools.terminal_record derive-stream` supports one fixed target interval.
- `recorded-sweep` supports config-defined fixed-cadence variants and semantic transition contracts.
- `seeded_jitter` and `interval_sequence` require a new schedule-driven derivation implementation. The skill must report this gap until that implementation exists.

Current fixed-cadence command shapes:

```bash
pixi run python -m tools.terminal_record derive-stream \
  --run-root <terminal-record-root> \
  --output-path <variant-snapshots-path> \
  --target-sample-interval-seconds <interval>

scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-sweep \
  --fixture-root <fixture-root> \
  --sweep <config-defined-sweep-name> \
  --demo-config <demo-config>
```

### Degraded-Cadence Evaluation Contract

Purpose: Decide whether a sparse or irregular replay remains semantically useful without demanding exact sample equality.

Inputs:

- Canonical transition timeline.
- One derived replay timeline.
- Required labels or ordered transition sequence.
- Required and forbidden terminal results.
- Maximum first-occurrence drift.
- Provider-independent and scenario-specific coherence invariants.

Core coherence invariants:

- State ordering must follow the scenario contract after unobserved short-lived states are removed.
- A variant must not invent `success`, `known_failure`, or `interrupted` when the scenario forbids it.
- Diagnostics loss must weaken certainty to an unknown or unavailable posture. It must not create a confident terminal claim.
- `tui_down` must not be followed by an ordinary ready or active state without explicit process-restart evidence.
- Repeated oscillation caused only by sparse sampling is a failure when it would mislead a downstream consumer.
- Missing an ephemeral state may be observational loss. Reversing a durable outcome is a tracker defect.

Verdicts:

| Verdict | Meaning |
| --- | --- |
| `pass` | Required transitions and terminal semantics are present, invariants hold, and drift is within the contract. |
| `degraded_but_coherent` | One or more short-lived observations are absent or delayed, but ordering, terminal meaning, and coherence invariants remain useful. |
| `fail` | The replay invents or reverses meaning, violates required ordering, exceeds a hard drift bound, oscillates misleadingly, or breaks an invariant. |
| `inconclusive` | Source evidence, labels, provider support, or replay capability is insufficient to judge the tracker. |

Outputs:

- Variant identity and realized sampling statistics.
- Required-state and transition coverage.
- Terminal-result checks.
- First-occurrence drift measurements.
- Coherence-invariant results.
- Missing-observation explanations.
- Verdict and issue references.

Validation:

- Degraded streams must never use strict per-sample equality as their sole acceptance rule.
- `degraded_but_coherent` requires a concrete observation-loss explanation.
- A forbidden terminal result always produces `fail`.
- Unsupported irregular replay produces `inconclusive`, not `pass`.

### Artifact Layout

Purpose: Keep intent, raw evidence, derived evidence, and verdicts separable and auditable.

```text
tmp/houmao-dev-testing/<run-id>/
  request.yaml
  resolved-manifest.json
  preflight.json
  managed/
    <provider>-<posture>/
      commands.ndjson
      runtime.json
      stdout.txt
      stderr.txt
      cleanup.json
  native-tui/
    scenario.md
    terminal-record/
      manifest.json
      session.cast
      pane_snapshots.ndjson
      labels.json
  replay-plan.yaml
  replay/
    <variant-id>/
      snapshots.ndjson
      parser_observed.ndjson
      state_observed.ndjson
      timeline.ndjson
      comparison.json
  issues/
    <issue-id>.md
  summary.json
  summary.md
```

Persistence rules:

- Raw capture is immutable after labeling begins. Derived streams live outside the source recorder root unless the existing command contract requires tagged outputs there.
- Every derived artifact records its source path, source digest, schedule, and source sample mapping.
- Secrets, auth files, and raw environment values are excluded from retained artifacts.
- Cleanup removes owned live processes and tmux sessions. It does not delete evidence unless the operator requests it.
- Committing a fixture requires an explicit redaction and provenance review.

Errors:

- `source_evidence_mutated`: A source digest changes after labels or derived streams exist.
- `artifact_provenance_missing`: A derived stream or report cannot identify its source and schedule.
- `sensitive_content_detected`: Retained or proposed committed evidence contains credential material or disallowed private content.

## Lifecycle And Persistence

| Phase | Entry Condition | Exit Condition | Durable Result |
| --- | --- | --- | --- |
| `planned` | User request accepted | Matrix and manifest resolve | Request and resolved manifest |
| `preflighted` | Manifest valid | Required tools and resources verified | Preflight report |
| `managed_tested` | Managed lanes selected | Launch, behavior, and cleanup checked | Managed lane artifacts |
| `capturing` | Clean native TUI and exact pane confirmed | Recorder stopped | Immutable source recording |
| `awaiting_labels` | Recording complete | Operator approves complete labels | Independent labels |
| `canonical_validated` | Labels valid | Source replay compared strictly | Canonical result |
| `cadence_validated` | Replay plan supported | All variants evaluated | Per-variant semantic results |
| `reported` | Required phases complete or explicitly skipped | Summary written and owned resources cleaned | Final summary and issues |

The skill must resume from durable artifacts where safe. It must revalidate source digests and live-resource ownership before continuing.

## Compatibility Notes

- The design uses `houmao-mgr` and `houmao-passive-server` as supported product surfaces. It does not use removed `houmao-cli`, standalone `houmao-server`, or standalone CAO launcher workflows.
- Python entrypoints run through `pixi run`.
- The current terminal recorder supports `claude`, `codex`, and `kimi` analysis.
- The current shared tracker has maintained profiles for Claude Code, Codex TUI, and Kimi Code. Other tools resolve to an unsupported profile.
- Gemini CLI is intentionally excluded even if residual Houmao code still exposes a Gemini path. The skill must not use test results to preserve or improve that pending-removal support.
- The existing demo contract claims robustness at 2 Hz or faster. Slower schedules are exploratory unless a scenario defines another bound.
- Fixed-cadence replay is available now. Irregular schedule replay is a planned extension and must remain capability-gated.
- Provider CLI flags change over time. The skill must inspect local orphan source references first, then installed `--help`, before embedding native launch details.

## Open Questions

- Should the irregular stream derivation command be `tools.terminal_record derive-stream --schedule <file>` or `run_demo.sh recorded-sweep --replay-plan <file>`?
- Should capture-rate health use a fixed percentile threshold, a maximum-gap threshold, or scenario-specific limits?
- Which coherence invariants should become executable shared contracts in `demo-config.toml`?
- Should `degraded_but_coherent` be a successful process exit with a warning, or a distinct non-zero result for CI policy to interpret?
- How should transcript redaction preserve terminal geometry and parser evidence without retaining sensitive text?
