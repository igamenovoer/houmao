# Shared TUI Tracking Demo Config Reference

This document explains the supported configuration contract for the shared tracked-TUI demo pack. The checked-in default config is `demo-config.toml` in the same directory. The machine-readable schema for that contract is packaged in `src/houmao/demo/shared_tui_tracking_demo_pack/schemas/demo_config.v1.schema.json`.

## Config Selection

The default operator workflow uses the companion config:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool claude
```

To switch to another config file, pass `--demo-config` on the operator-facing command:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start \
  --tool claude \
  --demo-config /path/to/alternate-demo-config.toml
```

The selected config file becomes the base config for that command. The demo does not merge the alternate file with the checked-in companion config. If you use custom config-derived roots such as a different `live_root` or `recorded_root`, use the same `--demo-config` again for later `inspect`, `stop`, `cleanup`, `recorded-validate-corpus`, or `recorded-sweep` calls unless you pass an explicit `--run-root` or `--fixtures-root`.

Each run persists the resolved config payload, including `source_config_path`, so later inspection can tell which file governed the run.

Each live-watch or recorded-capture run also writes a run-local `session_ownership.json` and publishes matching secret-free recovery pointers into the demo-owned tmux session environment. Normal `stop` uses that bookkeeping for graceful live-watch finalization. Forceful `cleanup` uses the same bookkeeping to recover stale demo-owned tmux sessions when graceful shutdown is no longer possible.

## Merge Order

The demo resolves config in this order:

1. Selected config file, defaulting to `scripts/demo/shared-tui-tracking-demo-pack/demo-config.toml`
2. Selected profile from `--profile`
3. Matching `scenario_overrides.<scenario_id>` when the command loads a scenario
4. CLI-owned overrides such as `--sample-interval-seconds`, `--settle-seconds`, `--review-video-fps`, or `--recipe`

The final merged result is what the demo persists into run artifacts and uses for launch, validation, and sweep behavior.

## Validation Behavior

The demo validates config in two steps:

1. The selected TOML file is validated as a supported demo-config document, including the shapes of `profiles`, `scenario_overrides`, and `sweeps`.
2. After profile, scenario, and CLI overrides are merged, the effective config is validated again before the workflow continues.

Validation is strict:

- unknown fields are rejected
- missing required top-level sections are rejected
- wrong value types are rejected
- invalid sweep layouts are rejected
- invalid render-cadence combinations such as `match_capture_cadence = false` without `fps` are rejected in the effective config

Failures identify the selected config path and the invalid field path.

## Top-Level Sections

### `schema_version`

Current schema version for the demo config contract. The packaged schema currently expects `1`.

### `demo_id`

Human-readable identity for the demo pack. The default value is `shared-tui-tracking-demo-pack`.

### `[paths]`

Repo-relative or absolute path roots used by the demo:

- `fixtures_root`: committed recorded-fixture corpus
- `recorded_root`: default output parent for recorded validation and capture outputs
- `live_root`: default output parent for live-watch runs
- `sweeps_root`: default output parent for sweep runs

If omitted inside the section, the implementation defaults match the checked-in companion config values.
Corpus-oriented commands such as `recorded-validate-corpus` now preflight this root and fail immediately when it is missing or contains no fixture manifests.

### `[tools.<tool>]`

Tool-specific launch defaults. The supported keys today are:

- `recipe_path`: brain recipe used when launching the selected tool
- `launch_overrides`: optional structured launch override contract; use the same `args` / `tool_params` shape accepted by brain recipes and direct builds
- `operator_prompt_mode`: optional launch policy request (`as_is` or `unattended`); omitted mode follows the normal unattended default

The demo currently expects both `tools.claude` and `tools.codex`.
The checked-in companion config points these recipe paths at the demo-owned `inputs/agents/presets/interactive-watch-<tool>-default.yaml` files. Those tracked presets keep `auth: default`, and each run materializes the concrete `tools/<tool>/auth/default` alias into the generated `workdir/.houmao/agents/` tree from the host-local fixture bundles under `tests/fixtures/auth-bundles/<tool>/`.

### `[evidence]`

Controls how evidence is captured around the tmux-backed demo session:

- `sample_interval_seconds`: live observation cadence, and recorder pane-snapshot cadence when recorder capture is enabled
- `runtime_observer_interval_seconds`: runtime liveness sampling cadence
- `ready_timeout_seconds`: timeout used by scenario steps that wait for a ready surface
- `cleanup_session`: whether a successful recorded-capture run reaps its tool tmux session after recorder shutdown; failures still use the shared ownership-based recovery path to avoid stale sessions
- `live_watch_recorder_enabled`: whether live watch retains passive terminal-recorder capture for replay debugging

If `runtime_observer_interval_seconds` is omitted, it defaults to the sample interval in the resolved config.

### `[semantics]`

Controls tracker-owned timing semantics:

- `settle_seconds`: delay before a success-candidate span settles into terminal success

### `[presentation.review_video]`

Controls rendered review-video output for recorded validation:

- `width`
- `height`
- `match_capture_cadence`
- `fps`
- `codec`
- `pixel_format`
- `keep_frames`

If `match_capture_cadence = true`, the review-video fps follows the capture cadence. If `match_capture_cadence = false`, the effective config must provide `fps`.

## Profiles

`[profiles.<name>]` contains partial override fragments. A profile can override any supported section that makes sense at config resolution time, such as `evidence`, `semantics`, `presentation`, `paths`, `tools`, or `sweeps`.

Example:

```toml
[profiles.fast_local.evidence]
sample_interval_seconds = 0.4
runtime_observer_interval_seconds = 0.4

[profiles.fast_local.presentation.review_video]
match_capture_cadence = false
fps = 3.0
```

Select a profile with:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-validate \
  --fixture-root tests/fixtures/shared_tui_tracking/recorded/claude/claude_explicit_success \
  --profile fast_local
```

## Scenario Overrides

`[scenario_overrides.<scenario_id>]` contains partial override fragments that apply only when a command resolves a scenario with that exact id. This matters primarily for `recorded-capture`, which loads one scenario JSON before config resolution finishes.

Use scenario overrides when a specific scenario needs a different recipe, settle timing, or capture cadence than the general demo default.

## Sweeps

`[sweeps.<name>]` defines a named robustness sweep. Each sweep contains:

- `description`
- `baseline_variant`
- `[[sweeps.<name>.variants]]`
- `[sweeps.<name>.contracts.<case_id>]`

Each variant defines one effective cadence. `use_source_cadence = true` means “use the original recording cadence”; otherwise the variant must declare `sample_interval_seconds`.

Each contract defines what must still hold for that fixture under the alternate cadence:

- `required_labels`
- `required_sequence`
- `required_terminal_result`
- `forbidden_terminal_results`
- `max_first_occurrence_drift_seconds`

`required_labels` keeps the older coarse contract shape: each label must appear, and its first appearance must stay in order with bounded drift against the baseline variant.

`required_sequence` is the stronger sequence-oriented contract for repeated lifecycles. It is matched as an ordered subsequence over the replayed transition labels and supports duplicates such as:

```toml
required_sequence = ["active", "ready_interrupted", "active", "ready_interrupted", "tui_down"]
```

Use `required_sequence` when the sweep needs to prove repeated transition families rather than only one first occurrence.

Sweep commands run one named sweep at a time:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-sweep \
  --fixture-root tests/fixtures/shared_tui_tracking/recorded/claude/claude_explicit_success \
  --sweep capture_frequency
```

The sweep command evaluates all variants inside that named sweep. It does not automatically run every sweep block in the config.

The checked-in `capture_frequency` sweep expresses the demo's current robustness claim: tracked public state is expected to remain robust only at `2 Hz` or faster, meaning `sample_interval_seconds <= 0.5`. Slower cadences should live in an alternate config and be treated as exploratory probes rather than default pass/fail expectations.

The checked-in sweep now uses `required_sequence` for repeated intentional-interruption cases so the default robustness claim can distinguish a single interrupted turn from two interrupted turns followed by close.
The same mechanism now also gates the maintained success-interrupt-success complex fixtures with a repeated ready-success / active / interrupted sequence such as:

```toml
required_sequence = ["ready_success", "active", "ready_interrupted", "active", "ready_interrupted", "ready_success"]
required_terminal_result = "success"
```

That contract stays intentionally coarse. Draft-specific judgments such as `last_turn=none` during `ready-draft` or `surface_editing_input=yes` during `active-draft` still belong in the strict replay-versus-ground-truth labels, not in the sweep-only vocabulary.

## Operator Examples

Use an alternate config for recorded capture:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh recorded-capture \
  --scenario scripts/demo/shared-tui-tracking-demo-pack/scenarios/claude-explicit-success.json \
  --demo-config /path/to/alternate-demo-config.toml
```

Use an alternate config for live watch, then inspect, stop, or clean up with the same config-derived roots:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start \
  --tool codex \
  --demo-config /path/to/alternate-demo-config.toml

scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh inspect \
  --demo-config /path/to/alternate-demo-config.toml \
  --json

scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh stop \
  --demo-config /path/to/alternate-demo-config.toml \
  --json

scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh cleanup \
  --demo-config /path/to/alternate-demo-config.toml \
  --json
```

Opt into recorder-backed live capture for replay debugging without changing the checked-in config:

```bash
scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start \
  --tool codex \
  --with-recorder
```
