## Purpose
Define the maintainer-facing `houmao-server` tracking-debug workflow used to reproduce and diagnose interactive lifecycle tracking behavior with persistent trace evidence.

## Requirements

### Requirement: Debug workflow SHALL provide opt-in dense server-side lifecycle trace streams
The system SHALL provide a maintainer-facing debug mode for `houmao-server` live TUI tracking that is disabled by default and enabled only through an explicit debug workflow or environment setting.

When enabled, the server SHALL emit structured trace events that cover, at minimum:

- CAO-compatible terminal input submission handling
- prompt-submission recording into the tracker
- turn-anchor arming, loss, and expiry
- per-cycle parsed-surface ingestion
- lifecycle reduction branch selection
- operator-state construction
- stability-signature updates
- transition publication or suppression

Each emitted event SHALL include enough metadata to correlate it with related events for the same tracked terminal and run.

#### Scenario: Normal server run stays free of dense debug tracing
- **WHEN** a maintainer runs `houmao-server` without enabling the tracking-debug workflow
- **THEN** the server does not emit the dense tracking-debug event streams
- **AND THEN** normal server and demo behavior remain unchanged

#### Scenario: Enabled debug run emits structured lifecycle-trace events
- **WHEN** a maintainer enables the tracking-debug workflow for a live watched terminal
- **THEN** the server writes structured trace events for the required tracking boundaries
- **AND THEN** those events include correlation keys such as terminal identity and event type so cross-module state flow can be reconstructed after the run

### Requirement: Debug workflow SHALL run an automatic two-path interactive repro
The system SHALL provide an automatic debug runner that exercises interactive lifecycle tracking through two distinct prompt-delivery paths against the same `houmao-server` shadow-watch substrate:

1. a server-owned input path that submits the prompt through the CAO-compatible terminal-input route
2. a direct tmux-input path that injects the prompt into the live pane without using the server input route

The runner SHALL collect the same classes of evidence for both paths so the results can be compared directly.

#### Scenario: Runner captures the server-owned input control path
- **WHEN** a maintainer runs the automatic tracking-debug workflow
- **THEN** the workflow submits at least one prompt through the server-owned terminal-input path
- **AND THEN** the resulting artifacts show whether prompt-submission recording and turn-anchor arming occurred for that prompt

#### Scenario: Runner captures the direct tmux-input comparison path
- **WHEN** a maintainer runs the automatic tracking-debug workflow
- **THEN** the workflow submits at least one prompt through direct tmux input into the live pane
- **AND THEN** the resulting artifacts show how the same watched-session lifecycle surface behaved without the server-owned input hook

### Requirement: Debug artifacts SHALL persist under a run-scoped repo-local `tmp/` root
When the automatic tracking-debug workflow is invoked without an explicit output directory, it SHALL write all generated artifacts under a fresh run directory rooted at:

```text
tmp/houmao-server-tracking-debug/
```

Each run directory SHALL preserve, at minimum:

- structured trace event streams
- inspect snapshots
- terminal or pane captures needed to correlate visible behavior with tracked state
- the effective tracking cadence and timing values used for that debug run
- a summary artifact that explains the observed differences between the two prompt paths

The workflow SHALL keep debug artifacts out of tracked repository paths.

#### Scenario: Default output root is repo-local and run-scoped
- **WHEN** a maintainer runs the tracking-debug workflow without overriding the output root
- **THEN** the workflow creates a fresh run directory under `tmp/houmao-server-tracking-debug/`
- **AND THEN** all debug artifacts for that run are stored beneath that run directory

#### Scenario: Debug output preserves both machine-readable traces and human-readable summary
- **WHEN** a tracking-debug run completes
- **THEN** the run directory contains machine-readable trace files and captured artifacts
- **AND THEN** it also contains a summary that identifies whether the observed failure came from missing prompt-submission anchoring, reduction behavior, transition suppression, or another traced branch outcome

### Requirement: Debug workflow SHALL label supplemental tmux and terminal-recording diagnostics clearly
The tracking-debug workflow SHALL clearly label supplemental transport evidence when it collects that evidence directly from tmux, including libtmux-backed pane inspection and workspace-available terminal-recording helpers, to explain what the live terminal visibly did during the run.

When such evidence is collected, the workflow SHALL keep it clearly labeled as supplemental diagnostics rather than the authoritative server-tracked state under investigation.

#### Scenario: Supplemental pane evidence explains server-state decisions without replacing them
- **WHEN** a maintainer enables supplemental tmux or terminal-recording capture during a tracking-debug run
- **THEN** the run artifacts include those captures alongside the server trace streams
- **AND THEN** the summary still treats the server-side lifecycle trace as the primary subject of analysis rather than treating the supplemental capture as the source of truth

### Requirement: Trace evidence SHALL make prompt-path causality explicit
The tracking-debug workflow SHALL make it possible to determine, from persisted artifacts alone, whether a prompt:

- reached the server-owned terminal-input route,
- caused prompt-submission recording,
- armed a tracker turn anchor,
- produced parsed-surface observations that entered the reduction pipeline, and
- resulted in published lifecycle transitions or in explicit suppression of those transitions

#### Scenario: Persisted evidence explains missing turn-anchor behavior
- **WHEN** a maintainer inspects a completed tracking-debug run where the direct tmux prompt path does not surface completion lifecycle
- **THEN** the persisted artifacts make clear whether no prompt-submission event was recorded for that path
- **AND THEN** the maintainer does not need to guess whether the missing lifecycle transition came from a bypassed input hook or a later tracker-stage failure

#### Scenario: Persisted evidence explains tracker-stage suppression after prompt submission
- **WHEN** a maintainer inspects a completed tracking-debug run where the server-owned input path still fails to surface the expected lifecycle state
- **THEN** the persisted artifacts make clear which tracker stage last advanced normally
- **AND THEN** the maintainer can identify whether the failure came from parsed-surface classification, reduction branching, stability handling, or transition publication
