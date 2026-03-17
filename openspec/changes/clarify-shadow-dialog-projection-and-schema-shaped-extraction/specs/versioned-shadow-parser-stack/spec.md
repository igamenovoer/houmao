## ADDED Requirements

### Requirement: Dialog projection processing is modular and swappable within the parser stack
The runtime-owned shadow parser stack SHALL resolve dialog projection through a provider-owned projection processor abstraction rather than by hardwiring all projection rules into one monolithic parser method.

For each parsed snapshot, the provider stack SHALL select exactly one projection processor instance.
That selection SHALL depend at minimum on the resolved provider parser preset/version and MAY additionally depend on matched output-variant evidence or other provider-owned snapshot evidence.

Projection processor selection SHALL remain isolated from runtime lifecycle monitoring so that changing projection logic for a provider/output family does not require changing runtime `TurnMonitor` logic or unrelated provider surface-classification code.

Projection provenance SHALL identify the selected processor instance through `projector_id`.

#### Scenario: Provider swaps projection processor for a known output family
- **WHEN** a provider parser preset or output family is mapped to a different projection processor implementation
- **THEN** the stack uses that selected processor to produce `DialogProjection`
- **AND THEN** runtime lifecycle logic continues to consume the resulting shared projection contract without requiring unrelated changes

#### Scenario: Projection processor selection is version-aware
- **WHEN** two provider versions require different dialog-cleanup logic for otherwise similar TUI snapshots
- **THEN** the stack may select different projection processor instances for those versions
- **AND THEN** the selection remains inside the parser stack rather than being spread across runtime lifecycle code

### Requirement: Shadow parser stack supports controlled projection-processor override
The runtime-owned shadow parser stack SHALL support controlled override of the projection processor used for a parsed snapshot so tests and advanced callers can swap projection behavior without rewriting provider parser classes.

This controlled override MAY be exposed through stack construction, provider parser construction, or another explicit injection point, but it SHALL remain narrower than arbitrary runtime plugin discovery.

#### Scenario: Test or advanced caller injects a projection processor override
- **WHEN** a test or advanced caller supplies an explicit projection processor override for a supported provider
- **THEN** the stack uses that processor for matching snapshots
- **AND THEN** the returned `DialogProjection.projection_metadata.projector_id` reflects the injected processor
