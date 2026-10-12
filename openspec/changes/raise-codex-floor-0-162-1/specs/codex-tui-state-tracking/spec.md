# Spec Delta

## MODIFIED Requirements

### Requirement: Codex delegated work remains active until the parent turn settles
For a maintained Codex 0.162.x TUI profile, visible multi-agent or collaboration activity SHALL count as current-turn active evidence. A parent turn SHALL remain active while delegated agents are running, waiting on current collaboration work, or reporting current progress, even if the editor frame remains visible.

The tracker SHALL report ready only after delegation activity has settled and the current surface satisfies the normal stable ready-return contract. Missed short-lived delegation frames at lower capture rates SHALL not create an impossible state sequence or a false successful completion before later active evidence.

#### Scenario: Running delegated agents keep the turn active
- **WHEN** the current Codex surface reports one or more delegated agents still running
- **THEN** tracked state remains active
- **AND THEN** the visible editor does not alone make the surface prompt-ready

#### Scenario: Sparse replay remains semantically valid
- **WHEN** a lower-rate replay skips one intermediate delegation transition
- **THEN** the resulting tracked sequence remains consistent with the observed later activity and stable ready return
- **AND THEN** the tracker does not emit an irreversible false terminal result between those observations

### Requirement: Codex current pending-input panes are active-turn evidence
For a maintained Codex 0.162.x TUI profile, a follow-up submitted while a turn is active SHALL be recognized from the queued-echo surface: a composer-style `› <text>` row rendered above the status row, disambiguated by in-flight turn content above the echo. A current queued echo SHALL contribute pending-input and active-turn evidence and SHALL prevent `surface.ready_posture=yes` even when the ordinary status row is hidden.

A queued echo accompanied by a `Worked for` dock or an interruption notice SHALL be treated as a turn-starting submission, not as pending input for the settled turn. Historical queued-echo text superseded by a later completed assistant response SHALL NOT by itself keep a settled prompt active.

When the queued echo collapses into a folded `+ N lines` expansion affordance, the single-snapshot layer SHALL report no positive pending-input evidence; recovering pending state across the collapse window is a tracker-level memory concern, not a scraping obligation.

#### Scenario: Pending steer does not hide the working row
- **WHEN** a current Codex surface shows a status row followed by a queued `› <text>` echo
- **THEN** the queued echo does not terminate the status-row scan as if it were an assistant response
- **AND THEN** the profile reports the turn as active and non-ready with pending-input evidence

#### Scenario: Pending steer remains busy while status row is hidden
- **WHEN** a current Codex surface shows a queued echo while streamed assistant output is growing and the status row is temporarily hidden
- **THEN** the queued echo independently keeps the current turn active

#### Scenario: Queued echo beside a turn dock is a new turn, not pending input
- **WHEN** a current Codex surface shows a `› <text>` echo together with a `Worked for` dock or interruption notice for the previous turn
- **THEN** the echo marks a turn-starting submission rather than pending input on the settled turn

#### Scenario: Collapsed queue echo has no single-snapshot pending evidence
- **WHEN** the queued echo has collapsed into a `+ N lines (^t to expand)` fold and no other current pending surface is visible
- **THEN** the profile does not report positive pending-input evidence from that snapshot alone
- **AND THEN** the profile does not manufacture pending state that only tracker-side submission memory could honestly provide

#### Scenario: Settled historical pending input does not remain active
- **WHEN** a later completed assistant response and clean current prompt supersede historical queued-echo text
- **THEN** the historical echo alone does not block current ready posture

### Requirement: Codex retry and list-selector activity is bounded to current source-backed surfaces
The Codex tracked-TUI profile SHALL recognize current reconnect activity from the maintained source-backed reconnect status family and SHALL NOT classify arbitrary prose or command descriptions containing `retry` as stream activity.

The profile SHALL treat a current model or list selector with a selection title or rows and the current list-selection confirmation footer (the 0.162 form `enter select · esc back`) as a blocking overlay. Historical selector titles or footers outside the current bounded interactive region SHALL NOT block a later prompt.

#### Scenario: Reconnect status is active
- **WHEN** the current Codex status surface displays `Reconnecting... 2/5` or the maintained equivalent reconnect status
- **THEN** the profile reports stream-retry active evidence and blocks ready-return success

#### Scenario: Retry prose is not activity
- **WHEN** current visible prose or a slash-command description contains the word `retry`
- **AND WHEN** no current reconnect status surface exists
- **THEN** the profile does not report stream-retry active evidence from that prose

#### Scenario: Model selector blocks prompt readiness
- **WHEN** the current Codex surface shows `Select Model and Effort` and the list-selection confirmation footer
- **THEN** the profile reports a blocking interactive surface
- **AND THEN** it does not classify the selected `› 1.` row as a submit-ready prompt draft

## ADDED Requirements

### Requirement: Codex busy evidence checks the status row before transcript prose
For codex versions at or above the support floor, the profile SHALL evaluate the bounded status-row label family (working, compaction, retry, and other maintained status labels) before treating a transcript line as assistant prose that terminates the activity scan. A visible compaction status row SHALL count as current active-turn evidence. Historical status rows in scrollback above the current turn SHALL NOT produce current active evidence.

#### Scenario: Compaction status row reads as busy
- **WHEN** the current Codex pane shows a `Compacting context (Ns • esc to interrupt)` status row at the live edge
- **THEN** the profile exposes active-turn evidence and not-ready posture for that snapshot

#### Scenario: Status label outside the legacy bullet prefixes still counts
- **WHEN** the current Codex status row carries a maintained status label that is not one of the historical hardcoded bullet prefixes
- **THEN** the status-row check still recognizes it as active evidence rather than swallowing the line as assistant prose

### Requirement: Codex lifecycle markers use the 0.162 surface forms
For codex versions at or above the support floor, the turn-completion dock marker SHALL be recognized as `Worked for Ns` text without the legacy box-drawing prefix, and the interruption surface SHALL be recognized by the `Conversation interrupted` prefix scoped to the live edge. An interruption notice SHALL count only when no concurrent status-row activity is visible, so stale scrollback notices do not mask a running turn.

#### Scenario: Worked-for dock marks turn completion
- **WHEN** the current Codex pane shows a `Worked for Ns • HH:MM` dock in the latest-turn region
- **THEN** the profile treats the turn as having completed for success-settlement purposes

#### Scenario: Interrupt notice with idle live edge marks interrupted
- **WHEN** the current Codex pane shows a `Conversation interrupted` notice at the live edge and no status-row activity is visible
- **THEN** the profile exposes interruption evidence for the current turn

#### Scenario: Interrupt notice with concurrent activity does not mask the turn
- **WHEN** a `Conversation interrupted` notice is visible and a current status row shows the turn still running
- **THEN** the profile does not expose interruption evidence from that notice alone

### Requirement: Codex 0.162.x operator surfaces block input admission
For codex versions at or above the support floor, the workspace-trust screen, list-selection pickers, the startup warnings screen, and the send-input-to-terminal dialog SHALL be blocking overlays: while one is mounted the surface reports not accepting input, not editing, not ready, and no pending input, and SHALL NOT manufacture success, interruption, or known failure. Recognition SHALL use bounded structure plus essential semantic tokens rather than exact full-sentence literals.

#### Scenario: Trust screen blocks admission under bypass
- **WHEN** codex is launched with bypass approvals and sandbox settings in an untrusted git workdir and shows `Trust this folder?`
- **THEN** the profile reports a blocking overlay with closed input admission and not-ready posture

#### Scenario: List picker blocks admission via the 0.162 footer
- **WHEN** the current Codex surface shows a selection list with the `enter select · esc back` footer
- **THEN** the profile reports a blocking overlay rather than a prompt-editing surface

#### Scenario: Startup warnings screen blocks admission
- **WHEN** the current Codex surface shows a `Warnings · N of M · Startup` screen with an `esc dismiss` affordance
- **THEN** the profile reports a blocking overlay until the warnings screen is dismissed

### Requirement: Codex temporal hints are dock-aware
For codex versions at or above the support floor, temporal active-turn evidence SHALL persist while latest-turn content grows and no `Worked for` dock has appeared, because 0.162 hides the status row while the final answer streams. Temporal hints SHALL end once the dock appears. A status-row absence of about one second or less with no dock SHALL NOT by itself end the turn. Temporal hints SHALL require current-turn content evidence, so startup or editing redraws do not manufacture activity.

#### Scenario: Streaming growth without a status row stays active
- **WHEN** recent Codex snapshots show latest-turn content growing, the status row is hidden, and no `Worked for` dock is present
- **THEN** the profile may expose temporal active-turn evidence for the shared tracker

#### Scenario: Docked Worked-for marker ends temporal hints
- **WHEN** a `Worked for` dock has appeared in the latest-turn region
- **THEN** temporal active-turn evidence for that turn ends even if later snapshots redraw nearby content

#### Scenario: Brief status-row blink does not end the turn
- **WHEN** the status row disappears for about one second or less mid-turn with no dock and turn content continues
- **THEN** the profile carries active evidence across the blink instead of manufacturing a ready seam

#### Scenario: Startup or editing redraw does not manufacture activity
- **WHEN** snapshot changes occur without current-turn content evidence such as an assistant bullet or numbered-stream line
- **THEN** the profile does not emit temporal active-turn evidence from redraw alone
