# UC-05 Pending Instruction State Dataset Report

## Scope

This dataset contains labeled tmux recordings for [UC-05: Detect Pending Instruction State](../usecases/uc-05-detect-pending-instruction-state.md). Each recording covers the prompt-queue lifecycle:

```text
ready → first prompt → processing → follow-up prompt while processing
  → pending visible → (additional follow-ups for count-targeted manifests)
  → pending consumed → processing again → done → ready
```

The labels are binary per-snapshot ground truth for two public-state fields plus an optional queue-depth estimate:

- `can_accept_input`: `yes` / `no` / `unknown`
- `has_pending_message`: `yes` / `no` / `unknown`
- `pending_count`: `0` / `1` / `2` / `3` / `"unknown"`

These binary labels map directly to the UC-05 posture vocabulary:

| `can_accept_input` | `has_pending_message` | UC-05 posture |
|---|---|---|
| `yes` | `no` | `ready_immediate` |
| `no` | `no` | `busy_active` |
| `no` | `yes` | `busy_pending_input` |
| `unknown` | `unknown` | unclassified (startup/transient) |

The `pending_count` field extends the original UC-05 dataset to capture cases with more than one prompt queued in the provider's internal input queue.

## Capture Methodology

- **Recorder**: `scripts/qualification/tui-prompt-admission/tui_pending_state_capture/runner.py`
- **Sample rate**: 20 Hz (`sample_interval_seconds = 0.05`)
- **Input mode**: direct tmux pane keystrokes, not gateway control
- **Calibration**: pattern-based visible-surface detection; no tracker-backed gates used during capture
- **Review video**: `review/labels.mp4` in each attempt directory
- **Prompts**: same canaries across providers
  - First prompt: `Count from 1 to 100 slowly, printing one number per second. Do not edit files.`
  - Second prompt: `Now count from 101 to 150 slowly, printing one number per second.`
  - Third prompt (2-pending / 3-pending-long): `Now count from 151 to 200 slowly, printing one number per second.`
  - Fourth prompt (3-pending-long only): ~482-character canary prompt ending with `[CANARY-500-CHARS-PENDING]`.

## Provider Matrix

| Provider | Calibrated version | Usable attempt | Total samples | Pending samples | Review video |
|---|---|---|---:|---:|---|
| Claude Code | 2.1.207 | `tmp/houmao-dev-testing/20260714-claude-pending-v2/claude-attempt-001` | 1,546 | 968 | `review/labels.mp4` |
| Codex CLI | 0.144.3 | `tmp/houmao-dev-testing/20260714-codex-pending-v2/codex-attempt-001` | 1,050 | 152 | `review/labels.mp4` |
| Kimi Code | 0.23.6 | `tmp/houmao-dev-testing/20260714-kimi-pending-v3/kimi-attempt-001` | 1,038 | 930 | `review/labels.mp4` |

### Count-Targeted Manifests

| Provider | Manifest | Target | Observed | Status | Usable attempt | Total samples | Pending samples |
|---|---|---:|---:|---|---|---|---:|
| Claude Code | `claude-1-pending.json` | 1 | 1 | success | `tmp/houmao-dev-testing/20260714-claude-1-pending/claude-attempt-001` | 1,595 | 1,004 |
| Claude Code | `claude-2-pending.json` | 2 | 1 | tainted (`pending_count_capped_at_1_target_2`) | `tmp/houmao-dev-testing/20260714-claude-2-pending/claude-attempt-001` | 71 | 30 |
| Claude Code | `claude-3-pending-long.json` | 3 | 1 | tainted (`pending_count_capped_at_1_target_3`) | `tmp/houmao-dev-testing/20260714-claude-3-pending-long/claude-attempt-001` | 187 | 112 |
| Codex CLI | `codex-1-pending.json` | 1 | 1 | success | `tmp/houmao-dev-testing/20260714-codex-1-pending/codex-attempt-001` | 684 | 571 |
| Codex CLI | `codex-2-pending.json` | 2 | 2 | success | `tmp/houmao-dev-testing/20260714-codex-2-pending/codex-attempt-001` | 1,091 | 126 |
| Codex CLI | `codex-3-pending-long.json` | 3 | 3 | success | `tmp/houmao-dev-testing/20260714-codex-3-pending-long/codex-attempt-001` | 1,178 | 134 |
| Kimi Code | `kimi-1-pending.json` | 1 | 1 | success | `tmp/houmao-dev-testing/20260714-kimi-1-pending/kimi-attempt-001` | 1,495 | 919 |
| Kimi Code | `kimi-2-pending.json` | 2 | 2 | success | `tmp/houmao-dev-testing/20260714-kimi-2-pending-v2/kimi-attempt-001` | 1,951 | 1,368 |
| Kimi Code | `kimi-3-pending-long.json` | 3 | 3 | tainted (`pattern_timeout_non_fatal:active`) | `tmp/houmao-dev-testing/20260714-kimi-3-pending-long-v4/kimi-attempt-001` | 2,922 | 1,964 |

If a provider caps its queue below the target count, the attempt is tainted with `pending_count_capped_at_N_target_M` and the evidence is still frozen. The cap is recorded in `capture/run-summary.json` and `capture/frozen-evidence.json`.

Kimi Code's `active` pattern matches tool/command turns (`Running a command`, `Running tool`, `Generating`, `Esc to interrupt`) but not pure text-generation turns, where the status bar only shows the static model/thinking-effort label. The post-pending `wait_for_pattern: active` step in the count-targeted manifests is marked `non_fatal_on_timeout` so the lifecycle completes and the run is tainted with `pattern_timeout_non_fatal:active` instead of failing.

## Artifact Layout

Each usable attempt follows the frozen evidence layout:

```text
<provider>-attempt-001/
  capture/
    lifecycle-manifest.json      # provider, version, patterns, ordered steps
    frozen-evidence.json         # digest evidence for the recording
    run-summary.json             # capture outcome and timing
    recording/
      manifest.json              # recorder metadata: 20 Hz, session, pane
      pane_snapshots.ndjson      # machine replay authority
      input_events.ndjson        # keystrokes injected into the pane
      session.cast               # human-review asciinema cast
      controller.log             # recorder controller log
      asciinema.log              # asciinema recorder log
      live_state.json            # final live state snapshot
  labels/
    labels.json                  # per-snapshot binary labels
    labels-summary.json          # span counts, sample ids, timings
  review/
    labels.mp4                   # labeled review video for human audit
```

## Label Span Summaries

### Claude Code 2.1.207

| Start (s) | End (s) | Samples | `can_accept_input` | `has_pending_message` | Interpretation |
|---:|---:|---:|---|---|---|
| 0.81 | 2.09 | 13 | `unknown` | `unknown` | startup / painter settle |
| 2.19 | 2.40 | 3 | `yes` | `no` | ready_immediate before first prompt |
| 2.50 | 5.63 | 31 | `no` | `no` | busy_active (first turn) |
| 5.73 | 111.32 | 968 | `no` | `yes` | busy_pending_input (second prompt queued) |
| 111.43 | 167.29 | 511 | `no` | `no` | busy_active (second turn) |
| 167.41 | 169.49 | 20 | `yes` | `no` | ready_immediate after done |

### Codex CLI 0.144.3

| Start (s) | End (s) | Samples | `can_accept_input` | `has_pending_message` | Interpretation |
|---:|---:|---:|---|---|---|
| 1.25 | 2.87 | 16 | `unknown` | `unknown` | startup / painter settle |
| 2.98 | 2.98 | 1 | `yes` | `no` | ready_immediate before first prompt |
| 3.09 | 19.35 | 152 | `no` | `yes` | busy_pending_input (second prompt queued) |
| 19.45 | 109.93 | 859 | `no` | `no` | busy_active (first + second turn) |
| 110.03 | 112.11 | 22 | `yes` | `no` | ready_immediate after done |

### Kimi Code 0.23.6

| Start (s) | End (s) | Samples | `can_accept_input` | `has_pending_message` | Interpretation |
|---:|---:|---:|---|---|---|
| 1.19 | 2.88 | 17 | `unknown` | `unknown` | startup / painter settle |
| 2.99 | 6.45 | 33 | `yes` | `no` | ready_immediate before first prompt |
| 6.55 | 10.19 | 35 | `no` | `no` | busy_active (first turn) |
| 10.31 | 108.37 | 930 | `no` | `yes` | busy_pending_input (second prompt queued) |
| 108.49 | 109.89 | 15 | `yes` | `no` | ready_immediate transient |
| 110.01 | 110.64 | 8 | `no` | `no` | final busy settle |

## Calibration Patterns

The patterns used for automated labeling are stored in each attempt's `capture/lifecycle-manifest.json`. Count-targeted manifests also include `pending_count_patterns`, which estimate queue depth from visible queued-message markers or inline counts.

### Claude Code

- `ready`: `(^|\n)\s*❯\s`
- `active`: `(Working\s*\(|Running\s+(tool|command)|Esc to interrupt|Ctrl\+C to interrupt|Flowing…|Thinking for|Cooked for)`
- `pending`: `(queued message|pending message|messages to be submitted|Press up to edit queued messages)`
- `pending_count`: `count_markers` over queued-message bullets

### Codex CLI

- `ready`: `(OpenAI Codex|permissions: YOLO mode|› )`
- `active`: `(Esc to interrupt|Working\s*\(|Running\s+(tool|command)|Starting MCP servers|background terminal running)`
- `pending`: `(Messages to be submitted after next tool call|messages to be submitted at end of turn|queued follow-up inputs|\n\s*↳\s)`
- `pending_count`: `count_markers` over `\n\s*↳\s` bullets

### Kimi Code

- `ready`: `(Welcome to Kimi Code!|@: mention files|> )`
- `active`: `(Running a command|Running tool|Generating|Esc to interrupt)`
- `pending`: `(❯ |to edit|ctrl-s to steer immediately|queued message|pending message)`
- `pending_count`: `count_markers` over queued-message bullets

## Partial and Failed Attempts

| Run root | Provider | Outcome | Note |
|---|---|---|---|
| `tmp/houmao-dev-testing/20260714-codex-pending/codex-attempt-002` | Codex | abandoned | early calibration run before pattern refinement |
| `tmp/houmao-dev-testing/20260714-kimi-pending-v2/kimi-attempt-001` | Kimi | failed | 0 `has_pending_message=yes` samples; second prompt did not visibly queue |
| `tmp/houmao-dev-testing/20260714-kimi-pending-v4/kimi-attempt-001` | Kimi | empty | no recorded samples |

## How to Reproduce

List available lifecycle manifests:

```bash
pixi run tui-pending-state-capture --list-lifecycles
```

Capture one provider with the default single-pending manifest:

```bash
pixi run tui-pending-state-capture \
  --provider codex \
  --run-root tmp/houmao-dev-testing/20260714-codex-pending-new
```

Capture a count-targeted manifest:

```bash
pixi run tui-pending-state-capture \
  --provider codex \
  --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/codex-3-pending-long.json \
  --run-root tmp/houmao-dev-testing/20260714-codex-3-pending-long
```

Skip the review video for faster iteration:

```bash
pixi run tui-pending-state-capture \
  --provider codex \
  --lifecycle scripts/qualification/tui-prompt-admission/lifecycles/codex-3-pending-long.json \
  --run-root tmp/houmao-dev-testing/20260714-codex-3-pending-long \
  --skip-video
```

## Related Artifacts

- Use case spec: [UC-05: Detect Pending Instruction State](../usecases/uc-05-detect-pending-instruction-state.md)
- Capture runner README: `scripts/qualification/tui-prompt-admission/tui_pending_state_capture/README.md`
- Lifecycle manifests: `scripts/qualification/tui-prompt-admission/lifecycles/{claude,codex,kimi}-{1-pending,2-pending,3-pending-long}.json`
- Calibration notes: `scripts/qualification/tui-prompt-admission/lifecycles/{claude,codex,kimi}-calibration.md`

## Open Gaps

- UC-06 (`houmao-mgr gateway prompt` pending-input guard) is not yet recorded. The current runner exercises only direct tmux keystrokes and does not drive the gateway/CLI prompt-control surface.
- Labeling is pattern-based; a human audit of `review/labels.mp4` for each provider is recommended before using the dataset to train or validate a detector.
- Count-targeted manifests are best-effort. Provider queue-depth caps and long-prompt rendering must be verified against the exact versions used in the capture environment.
- Claude Code caps its visible pending queue at one additional prompt; higher target counts are recorded as tainted cap evidence.
- Kimi Code does not render a distinct active indicator for pure text-generation turns, so the post-pending `active` wait is non-fatal.
