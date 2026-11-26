# Spec Delta

## ADDED Requirements

### Requirement: Managed runtime integration coverage remains representative
Brain-builder, launch, rebuild, and relaunch tests SHALL prove that managed defaults install the complete four-member static agent pack in copy mode and do not install admin public skills by default.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Representative integration coverage SHALL include policy override or disable behavior, reused-home synchronization, tool-native top-level siblings, shared child completeness, generated prompt route availability, auto-skill separation, collision rejection, and secret-free provenance without duplicating the low-level transaction matrix.

#### Scenario: Managed launch builds an agent home
- **WHEN** managed launch uses default system-skill policy
- **THEN** integration coverage verifies the agent entrypoint, shared routines, pro loop, and lite loop as top-level siblings
- **AND THEN** it verifies that no composed tree exists below the entrypoint

#### Scenario: Managed launch disables system skills
- **WHEN** managed launch uses a policy that disables system-skill installation
- **THEN** integration coverage verifies that all four agent-pack members are absent
- **AND THEN** generated prompts use their fallback posture

#### Scenario: Build integration keeps behavior boundaries covered
- **WHEN** managed system-skill policy is passed through source recipes, launch profiles, or managed launch resolution into brain construction
- **THEN** tests SHALL verify representative source additive behavior, profile override or disable behavior, collision rejection, tool-specific projection roots, and secret-free provenance

#### Scenario: Filesystem sync details stay in sync helper tests
- **WHEN** a brain-builder test exercises reused-home cleanup
- **THEN** it SHALL assert the integration outcome and provenance, while exact removal ordering and path preservation details SHALL be covered by managed-home sync helper tests

## REMOVED Requirements

### Requirement: Runtime integration coverage remains representative
**Reason**: The manual adoption coverage case is retired.
**Migration**: Verify supported managed launches with the default and with a policy that disables system skills.
