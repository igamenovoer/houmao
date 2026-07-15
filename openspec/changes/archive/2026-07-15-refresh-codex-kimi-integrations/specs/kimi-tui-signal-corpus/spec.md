## MODIFIED Requirements

### Requirement: Kimi signal corpus SHALL include high-rate and derived low-rate streams
For each required Kimi 0.23.x unattended TUI capture scenario, the corpus SHALL include a high-rate source snapshot stream sampled at about 20 fps and multiple derived lower-rate streams or delay schedules from that source.

Derived streams SHALL include at least one regular low-rate stream and one jittered stream that simulates variable TUI capture delay. Every derived sample SHALL preserve traceability to the source high-rate sample used to create it.

#### Scenario: Low-rate Kimi streams are derived from high-rate source
- **WHEN** a maintainer records one Kimi scenario at about 20 fps
- **THEN** tooling derives regular and jittered lower-rate streams from that source run
- **AND THEN** each derived sample preserves its source sample identity

#### Scenario: Replay validation covers rate and delay variation
- **WHEN** Kimi replay validation runs for one labeled scenario
- **THEN** validation compares tracker output against the high-rate manual labels
- **AND THEN** validation evaluates regular and jittered lower-rate streams against meaningful transition constraints

## ADDED Requirements

### Requirement: Maintained Kimi corpus targets unattended 0.23.x operation
The refreshed maintained Kimi corpus SHALL use Kimi 0.23.x in unattended mode. Normal scenario actions SHALL not request operator confirmation. If an unavoidable upstream hard-coded intervention appears, the corpus SHALL label it explicitly and record source evidence that no supported setting can suppress it.

#### Scenario: Ordinary unattended scenario has no confirmation state
- **WHEN** a maintained Kimi 0.23.x unattended scenario exercises normal prompts and tools
- **THEN** its labels contain no operator-confirmation state
- **AND THEN** any exception identifies the upstream hard-coded intervention and missing bypass setting

