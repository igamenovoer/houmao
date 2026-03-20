## MODIFIED Requirements

### Requirement: Monitor SHALL consume Houmao-server tracked state every 0.5 seconds and render a `rich` dashboard
The monitor process SHALL poll each tracked terminal through `houmao-server` every `0.5` seconds.

For each poll, the monitor SHALL consume the authoritative tracked-state payload exposed by `houmao-server` for that terminal. The monitor SHALL NOT require direct CAO terminal-output polling, a demo-local parser stack, or a demo-local lifecycle/state tracker in order to render current live state.

The live monitor session SHALL render a `rich` dashboard that makes it easy to compare both agents side by side while the operator interactively prompts Claude Code and Codex. At minimum, the dashboard SHALL show current server-owned transport/process/parse state, parser-facing surface fields, lifecycle state, lifecycle authority, stability, and lifecycle timing needed for operator validation.

The monitor SHALL keep a rolling transition log in the display so an operator can see state changes as they happen rather than only the latest steady-state row.

#### Scenario: Monitor updates current server-owned state on a fixed cadence
- **WHEN** the monitor session is active while the demo is running
- **THEN** it refreshes the displayed state for both agents every `0.5` seconds
- **AND THEN** the dashboard reflects the latest tracked state returned by `houmao-server` for each terminal

#### Scenario: Monitor does not re-derive tracked state locally
- **WHEN** the monitor renders current live state for a tracked terminal
- **THEN** it consumes the server-owned tracked-state payload as the authority
- **AND THEN** it does not run a second parser, lifecycle reducer, or state tracker to decide what state to display

### Requirement: Monitor SHALL expose server-owned parser, lifecycle, and timing fields needed for manual validation
For each agent, the live monitor SHALL expose at minimum:

- `transport_state`
- `process_state`
- `parse_status`
- parser availability
- parser business state
- parser input mode
- parser UI context
- readiness state
- completion state
- lifecycle authority metadata sufficient to tell whether completion is `turn_anchored` or `unanchored_background`
- visible-state stability metadata sufficient to tell whether the current server-tracked signature is stable and for how long
- projection-change indicator
- lifecycle timing information needed to understand unknown, candidate-complete, and stalled transitions
- recent anomaly codes

The monitor SHOULD also surface concise session metadata such as tool, terminal id, tmux session name, parser preset/version, detail text, and a short dialog tail when that information is available from `houmao-server`.

The monitor SHALL distinguish visible-state stability from completion debounce timing in both wording and layout. It SHALL NOT label completion debounce timing as if it were the general visible-state stability signal.
When the dashboard surfaces run timing knobs, it SHALL distinguish the monitor-local poll cadence from the server-owned completion debounce and unknown-to-stalled posture.

#### Scenario: Operator can distinguish parser state from lifecycle state without local reclassification
- **WHEN** the operator watches the monitor during manual interaction
- **THEN** the display separates raw tracked parser-facing fields from higher-level readiness and completion state
- **AND THEN** the operator can tell whether a surprising lifecycle transition came from transport loss, TUI-down state, parser availability, operator-blocked state, unknown timing, or projection change
- **AND THEN** that interpretation comes from server-owned tracked state rather than a second demo-local tracker

#### Scenario: Operator can distinguish visible stability from completion debounce
- **WHEN** the operator watches a session return to a quiet or steady-looking surface
- **THEN** the display makes clear whether the server is reporting a stable visible state, a candidate-complete completion state, or both
- **AND THEN** the monitor does not present completion debounce timing as the same concept as the general visible-state stability signal

#### Scenario: Operator can see completion authority directly
- **WHEN** a tracked session has no active server-owned turn anchor
- **THEN** the display exposes that completion is currently `unanchored_background`
- **AND THEN** the operator does not have to infer that authority state from transition history alone

#### Scenario: Operator can distinguish monitor cadence from server posture
- **WHEN** the dashboard shows run timing knobs during a live demo run
- **THEN** the display separates the monitor-local poll cadence from the server-owned completion debounce and unknown-to-stalled posture
- **AND THEN** the timing line does not present those unlike ownership domains as one undifferentiated `stable` signal

### Requirement: README SHALL teach the Houmao-owned manual state-validation workflow
The demo-pack README SHALL document:

- prerequisites,
- the standalone purpose of the pack,
- the dummy-project workdir posture,
- the supported `houmao-server + houmao-srv-ctrl` pair boundary,
- the start, inspect, attach, and stop workflow,
- that the operator manually prompts the live Claude Code and Codex TUIs while watching server-tracked state change in the monitor,
- the meaning of the displayed parser, lifecycle, lifecycle-authority, stability, and timing fields, and
- concrete manual interactions the operator can perform to validate state changes.

The README SHALL make clear that `houmao-server` is the authoritative live tracking surface for what the monitor displays and that the demo is a server-state observation surface rather than a second parser or lifecycle tracker.

#### Scenario: Maintainer can follow the README to perform a Houmao-server-based manual validation run
- **WHEN** a maintainer follows the README from a fresh checkout with prerequisites satisfied
- **THEN** they can start the demo, attach to the Claude and Codex sessions, watch the monitor session, and stop the run without hidden setup steps
- **AND THEN** the README explains that `houmao-server` is the authoritative live tracking surface for what the monitor displays

#### Scenario: Maintainer understands the prompt-and-observe purpose from the README
- **WHEN** a maintainer reads the README before running the demo
- **THEN** they understand that the intended workflow is to interactively prompt the live TUIs and observe how `houmao-server` tracked state changes
- **AND THEN** the README does not imply that the demo itself is the primary owner of parser, lifecycle, or state-tracking semantics

## ADDED Requirements

### Requirement: Active operator-facing demo copy SHALL preserve server ownership boundaries
Current active operator-facing demo copy under `scripts/demo/houmao-server-dual-shadow-watch/`, including the tracked projection profile and the interactive guide prose, SHALL describe the pack as a server-state observation surface and SHALL NOT frame it as the owner of parser, lifecycle, or tracking semantics.

#### Scenario: Projection demo profile avoids ownership drift
- **WHEN** a maintainer reads `scripts/demo/houmao-server-dual-shadow-watch/profiles/projection-demo.md`
- **THEN** the profile steers short observable prompt turns in the copied demo project
- **AND THEN** it does not claim that the demo itself owns parser or lifecycle validation semantics

#### Scenario: Interactive guide teaches prompt-and-observe workflow without renaming the harness surface
- **WHEN** a maintainer follows `scripts/demo/houmao-server-dual-shadow-watch/autotest/case-interactive-shadow-validation.md`
- **THEN** the guide teaches them to interactively prompt the live TUIs and observe `houmao-server` tracked state changes
- **AND THEN** the workflow does not depend on renaming the current autotest case identifier to achieve that reframing
