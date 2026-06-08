## ADDED Requirements

### Requirement: Kimi signal profiles SHALL be derived from recorded signal contracts
The Kimi Code TUI signal profile SHALL be implemented from the recorded Kimi signal corpus and change-local signal contract artifacts.

The Kimi signal contract SHALL combine live capture evidence with Kimi TUI source-code investigation. Detector rules SHALL identify whether each relied-on signal is source-backed component structure, source-backed styling, temporal behavior observed in capture, or bounded semantics within a known source-backed region.

The profile SHALL prefer minimal stable signals in this order:

1. explicit input events and timing
2. structural anchors in the current surface
3. ANSI/style facts
4. temporal behavior over recent frames
5. bounded semantic tokens inside known visual regions
6. exact string fragments only as diagnostic or fallback evidence

The profile SHALL scope activity and terminal evidence to current-turn or live-edge regions so stale transcript text does not control current state.

#### Scenario: Kimi detector uses structural and style anchors
- **WHEN** the Kimi profile classifies a ready editor or approval dialog
- **THEN** it uses structural anchors and style-aware facts documented in the signal contract
- **AND THEN** it does not depend primarily on one full exact text sentence from Kimi output

#### Scenario: Kimi detector ignores stale transcript activity
- **WHEN** older Kimi activity rows remain visible above the current ready editor region
- **THEN** the Kimi profile does not emit current active-turn evidence from those stale rows alone

#### Scenario: Kimi footer metadata does not imply active state
- **WHEN** a Kimi snapshot contains footer model metadata with `thinking`
- **AND WHEN** the current-turn region has no active response, tool, or spinner evidence
- **THEN** the Kimi profile does not emit active-turn evidence solely from that footer text

### Requirement: Kimi profile implementation SHALL pass recorded validation before maintained support
The Kimi shared TUI tracking profile SHALL pass the labeled Kimi recorded-validation corpus for both high-rate and derived low-rate streams before it is treated as a maintained profile.

The validation gate SHALL include ready, draft, active, completed, approval-blocked, approval-rejected, interrupted, and footer-metadata scenarios across at least 5 development live sessions and at least 3 held-out test live sessions.

Held-out test sessions SHALL NOT be used to choose detector rules, tune temporal thresholds, or revise the Kimi signal contract before the acceptance run.

#### Scenario: Kimi profile passes required scenario families
- **WHEN** Kimi profile implementation is complete
- **THEN** recorded validation passes for the required Kimi scenario families
- **AND THEN** both high-rate and derived low-rate replay outputs match the labeled public tracked-state expectations for development and held-out test sessions

#### Scenario: Held-out sessions guard against overfit detector rules
- **WHEN** Kimi detector rules pass the development corpus but fail held-out Kimi sessions
- **THEN** the Kimi profile is not treated as maintained
- **AND THEN** implementation must revise the signal contract or collect additional evidence before claiming maintained support

#### Scenario: Missing Kimi corpus prevents maintained-profile claim
- **WHEN** no labeled Kimi corpus exists for a required scenario family
- **THEN** the Kimi profile is not treated as maintained for that scenario family
- **AND THEN** implementation must either add the missing capture evidence or narrow its maintained support claim
