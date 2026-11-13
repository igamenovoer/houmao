## MODIFIED Requirements

### Requirement: Maintained Kimi corpus targets current-floor operation including operator surfaces
The refreshed maintained Kimi corpus SHALL use kimi-code at or above the current support floor (2.1.1). Unattended lifecycle scenarios SHALL NOT request operator confirmation beyond the startup trust modal. Operator-interaction scenarios (approvals, plan review, question dialogs, trust modal) SHALL be captured deliberately in manual permission mode and labeled like any other state family.

Managed-session corpus evidence SHALL record that native role-prompt projection completed before provider startup and that no role-bootstrap chat turn occurred. A canceled capture or replay task SHALL NOT establish qualification or waive the recorded-validation gate.

#### Scenario: Ordinary unattended scenario has no confirmation state beyond startup trust
- **WHEN** a maintained Kimi unattended scenario exercises normal prompts and tools on a fresh untrusted workdir
- **THEN** its labels contain no operator-confirmation state except the startup workspace-trust modal
- **AND THEN** any other exception identifies the upstream hard-coded intervention and missing bypass setting

#### Scenario: Operator-interaction scenario captures modal states deliberately
- **WHEN** a maintained Kimi scenario drives an approval, plan-review, or agent-question surface in manual permission mode
- **THEN** the corpus labels the modal span with the same eight-field public-state ground truth as lifecycle spans
- **AND THEN** the scenario records the operator choice made as an input event

#### Scenario: Managed startup uses the native role prompt
- **WHEN** a maintained Kimi managed-session recording is used as native role-prompt evidence
- **THEN** its metadata identifies the current supported version and successful pre-start SYSTEM.md projection
- **AND THEN** the first conversational input is workload content rather than a role-bootstrap turn

#### Scenario: Older corpus is historical only
- **WHEN** a recording captured Kimi below the current 2.1.1 support floor
- **THEN** it may remain historical evidence but does not qualify the maintained Kimi profile
