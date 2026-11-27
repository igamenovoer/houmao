# Spec Delta

## ADDED Requirements

### Requirement: Managed Hermes Profile Cleanup Resolves Both Owned Artifacts

Explicit removal of an eligible managed Hermes home SHALL separately verify the native profile and the project link from the recorded owner binding. Cleanup SHALL use native profile deletion and unlink only the verified project link. Dry-run SHALL show both actions and their eligibility without changing either artifact.

#### Scenario: An Eligible Retired Profile Is Removed

- **WHEN** cleanup selects a retired named-profile home with no preserved runtime references and verified native quiescence
- **THEN** it removes the exact owned profile through Hermes native lifecycle and settles the profile's routing identity
- **AND THEN** it removes the verified project symlink itself and preserves the shared installation, gateway, and sibling profiles

#### Scenario: A Profile Still Has a Preserved Runtime Reference

- **WHEN** a current or preserved runtime still references the profile selected by build cleanup
- **THEN** cleanup records both artifacts as preserved and leaves the profile available for its supported lifecycle

#### Scenario: An Artifact or the Native Reservation Is Unverified

- **WHEN** ownership is missing, the project entry now points elsewhere, or the profile still has a native owner or unsettled writer
- **THEN** cleanup reports the blocking condition and preserves the unverified entry or native state
- **AND THEN** the project link alone cannot authorize native deletion

#### Scenario: Cleanup Is Retried After Partial Success

- **WHEN** native profile deletion or unlink has partially completed, or Hermes reports pending identity settlement
- **THEN** cleanup retains the exact owner binding, distinguishes completed steps from remaining work, and can safely retry against the same profile identity
- **AND THEN** it cannot delete a replacement profile or unrelated file found under a reused name
