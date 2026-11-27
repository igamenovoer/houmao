# Spec Delta

## ADDED Requirements

### Requirement: Hermes Managed-Self Access Requires Current Profile Authority

For named-profile Hermes workers, Houmao SHALL require the current verified served-profile binding before loading a self signer or admitting a signed self effect. It SHALL match the requested target, execution context, managed generation, gateway incarnation, profile authority, and registration revision. The signing client SHALL additionally verify profile-specific native caller origin.

#### Scenario: Concurrent Workers Sign Their Own Operations

- **WHEN** two current tool callers from different profiles on one verified Hermes gateway invoke their own protected Houmao operations
- **THEN** each signs with the key registered for its own managed generation and target listener
- **AND THEN** proof from one worker cannot grant an effect on the sibling's gateway

#### Scenario: Shared Host Survives a Worker Stop

- **WHEN** the shared Hermes gateway remains live but one selected profile is parked, replaced, or no longer has current binding evidence
- **THEN** the signing client and receiving ingress refuse that worker's stale self authority even while a sibling continues to sign

#### Scenario: Profile Authority Changes After Challenge Admission

- **WHEN** a self-authorized effect is pending and the selected worker's generation or profile authority changes before execution
- **THEN** current authority checks reject the stale effect
- **AND THEN** successful native reattachment can use only current authorized identity and evidence
