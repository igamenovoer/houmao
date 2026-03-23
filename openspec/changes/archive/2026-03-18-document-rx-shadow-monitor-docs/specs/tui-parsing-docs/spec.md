## ADDED Requirements

### Requirement: TUI parsing docs describe the shipped runtime monitor architecture
The repository SHALL publish TUI parsing documentation that describes the current CAO `shadow_only` runtime monitor architecture as implemented after `rx-shadow-turn-monitor`.

At minimum, the maintained explanation SHALL make clear that:

- provider parsers still classify one snapshot into `SurfaceAssessment` and `DialogProjection`,
- runtime lifecycle monitoring now lives in `src/houmao/agents/realm_controller/backends/cao_rx_monitor.py`,
- current-thread CAO polling remains in `src/houmao/agents/realm_controller/backends/cao_rest.py`, and
- the published docs no longer describe `_TurnMonitor` in `cao_rest.py` as the current implementation.

#### Scenario: Developer guide points readers to the shipped runtime monitor sources
- **WHEN** a maintainer reads the TUI parsing architecture or lifecycle docs
- **THEN** those docs identify `cao_rx_monitor.py` and `cao_rest.py` as the current runtime monitor implementation surfaces
- **AND THEN** the docs do not present `_TurnMonitor` in `cao_rest.py` as the shipped lifecycle implementation

### Requirement: TUI parsing lifecycle docs explain current completion and stall semantics
The TUI parsing docs SHALL explain the shipped readiness and completion semantics introduced by the Rx monitor rewrite.

At minimum, the maintained explanation SHALL cover:

- readiness and completion as separate runtime monitoring phases,
- the completion stability window controlled by `completion_stability_seconds`,
- the rule that later state changes reset a pending completion window,
- the rule that any known observation cancels a pending unknown-to-stalled timer,
- mailbox observer bypass behavior for definitive completion payloads, and
- the distinction between parser snapshot state and runtime lifecycle classification.

#### Scenario: Docs explain why transient idle does not complete a turn
- **WHEN** a maintainer or operator reads the lifecycle explanation for `shadow_only`
- **THEN** the docs explain that one idle observation after post-submit activity is insufficient for completion
- **AND THEN** they explain that sustained idle over `completion_stability_seconds` is required unless a caller-owned completion observer returns a definitive result

#### Scenario: Docs explain stalled recovery and timer reset behavior
- **WHEN** a maintainer or operator reads the lifecycle explanation for `unknown` and `stalled`
- **THEN** the docs explain that a known observation resets pending unknown-to-stalled timing
- **AND THEN** they do not describe the shipped stall behavior as a fixed wall-clock timer that ignores recovery observations

### Requirement: TUI parsing docs use the correct shadow text-surface boundaries
The maintained TUI parsing docs SHALL preserve the current boundary between `DialogProjection.normalized_text` and `DialogProjection.dialog_text`.

At minimum, the docs SHALL state that:

- `normalized_text` remains the closer-to-source normalized snapshot surface,
- lifecycle change evidence for the current runtime monitor is based on normalized shadow text after pipeline normalization,
- `dialog_text` remains a best-effort dialog-oriented projection for human inspection and caller-owned extraction patterns, and
- `dialog_text` SHALL NOT be documented as the shipped runtime monitor's lifecycle-diff basis.

#### Scenario: Shared contract docs distinguish lifecycle evidence from projected dialog
- **WHEN** a reader consults the shared contract or provider docs to understand shadow text surfaces
- **THEN** those docs explain that `normalized_text` and `dialog_text` have different roles
- **AND THEN** they do not present `dialog_text` as the current runtime monitor's coarse diff surface

### Requirement: Shadow parsing reference docs expose the current shadow policy and diagnostics
The reference and troubleshooting docs for CAO shadow parsing SHALL document the current runtime-owned shadow policy and the user-visible diagnostics surfaces that accompany it.

At minimum, that coverage SHALL include:

- `runtime.cao.shadow.unknown_to_stalled_timeout_seconds`,
- `runtime.cao.shadow.completion_stability_seconds`,
- `runtime.cao.shadow.stalled_is_terminal`,
- the corresponding diagnostics fields surfaced in shadow-mode results, and
- the current operator-facing explanation of timeout, blocked, stalled, and completion symptoms in `shadow_only`.

#### Scenario: Operator can find the completion stability policy in reference docs
- **WHEN** an operator reads the main runtime reference or shadow troubleshooting guide
- **THEN** those docs describe `completion_stability_seconds` alongside the other `runtime.cao.shadow` policy fields
- **AND THEN** the operator does not need to infer that setting only from source code or change artifacts

#### Scenario: Troubleshooting docs explain current completion timeout behavior
- **WHEN** an operator reads the troubleshooting entry for a turn completion timeout while visible dialog is present
- **THEN** the docs explain the current post-submit activity and stability-window rules
- **AND THEN** they do not describe the old immediate-completion behavior as current runtime semantics

### Requirement: TUI parsing docs remain discoverable and source-aligned
The maintained TUI parsing docs SHALL remain discoverable from the existing docs entrypoints and SHALL point readers to the source materials they reflect.

If implementation work adds a new focused TUI parsing developer page, the relevant docs indexes SHALL link to it explicitly.

At minimum, the maintained TUI parsing explanation SHALL identify the key source materials it reflects, including the runtime monitor sources and the behavior-defining Rx monitor tests.

#### Scenario: Reader can reach the maintained TUI parsing explanation from docs indexes
- **WHEN** a reader starts from `docs/index.md`, `docs/reference/index.md`, or `docs/developer/tui-parsing/index.md`
- **THEN** those entrypoints link to the maintained TUI parsing explanation pages
- **AND THEN** any new focused TUI parsing page added by this change is linked from the relevant index pages

#### Scenario: Detailed TUI parsing docs identify the source materials they reflect
- **WHEN** a maintainer opens the detailed TUI parsing docs to verify a contract or refresh the docs later
- **THEN** the docs identify the relevant implementation files, tests, or completed change artifacts that define the documented behavior
- **AND THEN** future maintainers have a clear source trail for keeping the docs aligned
