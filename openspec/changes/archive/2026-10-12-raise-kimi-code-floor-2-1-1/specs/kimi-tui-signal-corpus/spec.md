# Spec Delta

## REMOVED Requirements

### Requirement: Maintained Kimi corpus targets unattended 0.23.x operation
**Reason**: kimi-code below the 2.1.1 support floor is unsupported, and operator-interaction surfaces (trust modal, approvals, plan review, question dialogs) are now deliberately in scope, so an unattended-only 0.23.x corpus cannot qualify the maintained detector.
**Migration**: Regenerate the corpus from kimi-code 2.1.1-or-later captures, including operator-interaction scenario families; the 2026-10-10 debug-campaign sessions seed the fixtures.

## ADDED Requirements

### Requirement: Maintained Kimi corpus targets current-floor operation including operator surfaces
The refreshed maintained Kimi corpus SHALL use kimi-code at or above the current support floor (2.1.1). Unattended lifecycle scenarios SHALL NOT request operator confirmation beyond the startup trust modal. Operator-interaction scenarios (approvals, plan review, question dialogs, trust modal) SHALL be captured deliberately in manual permission mode and labeled like any other state family.

#### Scenario: Ordinary unattended scenario has no confirmation state beyond startup trust
- **WHEN** a maintained Kimi unattended scenario exercises normal prompts and tools on a fresh untrusted workdir
- **THEN** its labels contain no operator-confirmation state except the startup workspace-trust modal
- **AND THEN** any other exception identifies the upstream hard-coded intervention and missing bypass setting

#### Scenario: Operator-interaction scenario captures modal states deliberately
- **WHEN** a maintained Kimi scenario drives an approval, plan-review, or agent-question surface in manual permission mode
- **THEN** the corpus labels the modal span with the same eight-field public-state ground truth as lifecycle spans
- **AND THEN** the scenario records the operator choice made as an input event
