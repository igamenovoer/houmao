## MODIFIED Requirements

### Requirement: Explore harness SHALL replay recorded observations through an independent ReactiveX tracker
The harness SHALL provide a harness-owned replay adapter over the shared TUI tracking core that consumes recorded snapshot observations and emits the simplified turn-state model using ReactiveX-driven timing rather than manual wall-clock bookkeeping.

That replay adapter SHALL remain outside of `houmao-server` implementation ownership and SHALL NOT import the server live-tracker adapter as the reducer under test.

The replay adapter SHALL instead consume the repo-owned shared TUI tracking core so that replay semantics match the official tracked-state contract without maintaining a separate mirrored reducer implementation inside the harness.

For this requirement, the required independence is from the live server adapter and from the content-first groundtruth path. It SHALL NOT be satisfied by keeping a parallel replay reducer architecture inside the harness.

At minimum, the replay adapter SHALL be able to emit:

- current turn phase `ready | active | unknown`
- terminal turn result `success | interrupted | known_failure | none`
- replay-timed settle behavior needed to distinguish active answer growth from settled success

#### Scenario: Replay tracker uses shared core without depending on the server adapter
- **WHEN** the harness replays recorded Claude observations
- **THEN** it invokes the shared TUI tracking core through a harness-owned replay adapter rather than the live server tracker
- **AND THEN** replay semantics stay aligned with the official contract without importing `houmao-server` adapter code

#### Scenario: Replay tracker emits settled success only after replayed settle timing
- **WHEN** a recorded Claude run shows answer content followed by a stable completion marker and returned prompt posture
- **THEN** the replay adapter does not emit `success` immediately when answer text first appears
- **AND THEN** it emits `success` only after the replayed settle timing confirms the stable terminal surface
