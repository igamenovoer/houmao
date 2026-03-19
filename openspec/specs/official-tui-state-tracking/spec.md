## Purpose
Define the server-owned live TUI tracking contract for direct tmux/process observation, official parsing, in-memory tracked state, and stability metadata.

## Requirements

### Requirement: Known tmux-backed sessions are tracked continuously
The system SHALL continuously track every known tmux-backed Houmao session while its tmux session exists, independent of whether any client is currently querying state and independent of whether a prompt was recently submitted.

Known sessions SHALL be seeded from `houmao-server` registration records for sessions that this server manages, enriched by manifest-backed metadata, and verified against live tmux liveness rather than by ad hoc CAO polling alone.

Shared live-agent registry records MAY be consulted as compatibility evidence or alias enrichment, but they SHALL NOT by themselves create an authoritative known-session entry for this capability.

#### Scenario: Background tracking continues without active queries
- **WHEN** a known tmux-backed session remains alive and no caller is polling its live state
- **THEN** the system continues tracking that session in the background
- **AND THEN** the latest live state remains current without requiring a request-triggered refresh

#### Scenario: Newly discovered known session enters continuous tracking
- **WHEN** the server discovers a newly known tmux-backed Houmao session through its registration or manifest-backed discovery path
- **THEN** the system starts continuous tracking for that session
- **AND THEN** the session no longer depends on a first state query to become watch-active

#### Scenario: Startup rebuild reuses server registration and live tmux verification
- **WHEN** `houmao-server` restarts and loads a server-managed registration record for a session whose tmux session is still live
- **THEN** the system re-admits that session into the known-session registry
- **AND THEN** manifest-backed metadata may enrich the tracked identity before background tracking resumes

#### Scenario: Shared registry evidence alone does not admit a watched session
- **WHEN** a shared live-agent registry record exists without an authoritative server registration record or a verifiable live tmux target for that session
- **THEN** that registry record alone does not create a primary known-session entry for this capability
- **AND THEN** the system does not start a background watch worker solely from that compatibility evidence

### Requirement: TUI liveliness is derived from process inspection
For each tracked tmux-backed session, the system SHALL determine whether the supported interactive TUI is up or down by inspecting the live process tree attached to the tracked tmux pane rather than by inferring that state only from captured pane text.

#### Scenario: TUI process is down while tmux remains alive
- **WHEN** a tracked tmux session still exists but the expected supported TUI process is no longer running in the tracked pane process tree
- **THEN** the tracked live state records that the TUI is down
- **AND THEN** the session remains under background tracking instead of being dropped immediately

#### Scenario: TUI process is up and eligible for parsing
- **WHEN** a tracked tmux session exists and the expected supported TUI process is running in the tracked pane process tree
- **THEN** the system treats the TUI as up for that cycle
- **AND THEN** the parsing stage may consume directly captured pane text for live state reduction

### Requirement: Parsed TUI state comes from direct tmux capture through the official parser
For supported live TUI tools, the system SHALL capture pane content directly from tmux and SHALL derive parsed live state through the repo-owned official parser stack for that tool.

The parsing and state-tracking path SHALL NOT require `cao-server` terminal-status or terminal-output endpoints as the authoritative source for live TUI interpretation.

#### Scenario: Supported live TUI snapshot is parsed directly from tmux capture
- **WHEN** a tracked supported TUI session is up and the server captures pane content directly from tmux
- **THEN** the system parses that captured content through the official parser stack
- **AND THEN** the resulting parsed state becomes the live interpretation surface for that cycle

#### Scenario: CAO is not the parsing authority for tracked state
- **WHEN** the system updates live tracked state for a supported tmux-backed session
- **THEN** it does not rely on child `cao-server` output or status polling as the parsing authority
- **AND THEN** the tracked state remains available even when the CAO parsing path is intentionally bypassed

### Requirement: Live tracked state distinguishes transport, process, and parse outcomes explicitly
The tracked-state contract SHALL expose at minimum:

- tracked session identity,
- any `terminal_id` compatibility alias used by the public route surface,
- `transport_state`,
- `process_state`,
- `parse_status`,
- optional `probe_error` detail,
- optional `parse_error` detail,
- nullable parsed TUI surface, and
- derived operator-facing live state.

For supported parsed tools, parse failure SHALL be represented explicitly rather than fabricated as a successful parsed surface.

#### Scenario: Parser failure is explicit in live tracked state
- **WHEN** the tmux session is live, the supported TUI process is up, and the official parser fails for that cycle
- **THEN** the live tracked state records an explicit parse-failure status
- **AND THEN** the parsed-surface field is absent or null for that cycle

#### Scenario: TUI-down cycle still exposes transport and process state
- **WHEN** the tmux session remains live but the expected supported TUI process is down
- **THEN** the live tracked state still exposes the transport and process fields for that session
- **AND THEN** the parse stage is represented as skipped or unavailable for that cycle

### Requirement: Live tracked state is authoritative in memory
The authoritative live tracked state for this capability SHALL live in server memory.

That in-memory state SHALL include at minimum:

- tracked session identity,
- `terminal_id` compatibility aliases,
- tmux transport state,
- TUI process liveliness,
- parse-stage status plus any probe or parse error detail,
- latest parsed TUI surface state when available,
- derived operator-facing live state, and
- bounded recent transitions or recent-state history.

The system SHALL NOT require per-session watch snapshot files or append-only watch logs as part of the authoritative contract for this capability.

#### Scenario: State query reads the current in-memory authority
- **WHEN** a caller requests live tracked state for a watched session
- **THEN** the system returns the latest state held in server memory
- **AND THEN** that result does not depend on reading a persisted watch snapshot file first

#### Scenario: Restart rebuilds live state from rediscovery
- **WHEN** the server restarts while some previously tracked tmux sessions are still alive
- **THEN** the system rebuilds live tracked state by rediscovering those live known sessions
- **AND THEN** it does not claim prior watch files as the authoritative source for the rebuilt state

### Requirement: Live tracking exposes stability metadata over the visible state signature
The system SHALL track how long the operator-visible live state signature remains unchanged and SHALL expose stability metadata for that signature as part of the in-memory tracked state.

At minimum, that stability metadata SHALL include whether the current signature is considered stable and how long it has remained unchanged.

#### Scenario: Unchanged live signature accumulates stability duration
- **WHEN** the operator-visible tracked state signature remains unchanged across successive observations
- **THEN** the system increases the tracked stability duration for that signature
- **AND THEN** the live state reflects that unchanged duration in its stability metadata

#### Scenario: Changed live signature resets stability duration
- **WHEN** any operator-visible component of the tracked state signature changes
- **THEN** the system resets the stability duration for the new signature
- **AND THEN** the live state no longer reports the prior signature's accumulated duration

### Requirement: Live tracked state exposes lifecycle timing and stalled classification for consumer dashboards
For supported parsed tmux-backed sessions, the system SHALL keep server-owned lifecycle reduction that is rich enough for consumer dashboards to preserve manual-validation semantics without re-implementing parser timing logic outside `houmao-server`.

At minimum, that server-owned lifecycle view SHALL include:

- readiness states that distinguish `ready`, `waiting`, `blocked`, `failed`, `unknown`, and `stalled`
- completion states that distinguish `inactive`, `in_progress`, `candidate_complete`, `completed`, `blocked`, `failed`, `unknown`, and `stalled`
- lifecycle timing metadata that includes:
  - `readiness_unknown_elapsed_seconds`
  - `completion_unknown_elapsed_seconds`
  - `completion_candidate_elapsed_seconds`
  - `unknown_to_stalled_timeout_seconds`
  - `completion_stability_seconds`

The system SHALL treat those lifecycle states and timings as part of the authoritative server-owned tracked state rather than as a demo-local interpretation layer.

#### Scenario: Continuous unknown readiness enters stalled in server-owned state
- **WHEN** the tracked readiness surface remains unknown for stall purposes continuously for `unknown_to_stalled_timeout_seconds`
- **THEN** the server-owned tracked state reports readiness as `stalled`
- **AND THEN** the corresponding tracked-state payload exposes the unknown elapsed timing that led to that transition

#### Scenario: Candidate-complete timing is exposed before completion
- **WHEN** a tracked session has armed completion monitoring from a previously ready baseline
- **AND WHEN** the parsed surface returns to submit-ready after post-submit activity
- **AND WHEN** the parsed surface remains a completion candidate but has not yet satisfied `completion_stability_seconds`
- **THEN** the server-owned tracked state reports completion as `candidate_complete`
- **AND THEN** the tracked-state payload exposes the elapsed candidate-complete timing for that cycle

#### Scenario: State queries can consume lifecycle timing without local recomputation
- **WHEN** a caller queries the authoritative tracked state for a live supported session
- **THEN** the response includes the current lifecycle states and lifecycle timing metadata needed to interpret unknown, candidate-complete, completed, and stalled transitions
- **AND THEN** the caller does not need to replay terminal text or re-run parser timing logic locally to obtain those values
