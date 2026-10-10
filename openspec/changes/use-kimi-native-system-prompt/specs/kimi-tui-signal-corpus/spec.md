## RENAMED Requirements

- FROM: `Maintained Kimi corpus targets unattended 0.23.x operation`
- TO: `Maintained Kimi corpus establishes the unattended 0.34.x baseline`

## MODIFIED Requirements

### Requirement: Maintained Kimi corpus establishes the unattended 0.34.x baseline
The refreshed maintained Kimi corpus SHALL use Kimi 0.34.x in unattended mode as baseline evidence for the unbounded `>=0.34.0` support range and SHALL include startup evidence that the managed native role prompt was projected without a bootstrap chat turn. Normal scenario actions SHALL not request operator confirmation. If an unavoidable upstream hard-coded intervention appears, the corpus SHALL label it explicitly and record source evidence that no supported setting can suppress it.

No Kimi corpus recorded against a version earlier than 0.34.0 SHALL establish maintained compatibility after this change.

#### Scenario: Ordinary unattended scenario has no confirmation or role-bootstrap state
- **WHEN** a maintained Kimi 0.34.x unattended scenario exercises normal prompts and tools
- **THEN** its labels contain no operator-confirmation or role-bootstrap chat state
- **AND THEN** any exception identifies the upstream hard-coded intervention and missing bypass setting

#### Scenario: Older corpus is historical only
- **WHEN** a recording captured Kimi 0.23.x or an earlier release
- **THEN** the corpus may be retained only as explicitly historical evidence
- **AND THEN** registry qualification does not use it to select a maintained Kimi profile
