## ADDED Requirements

### Requirement: Dialog projection processing is modular and swappable within the parser stack
The runtime-owned shadow parser stack SHALL resolve dialog projection through a provider-owned projection processor abstraction rather than by hardwiring all projection rules into one monolithic parser method.

For each parsed snapshot, the provider parser SHALL select exactly one projection processor instance.
The projection processor contract SHALL be a repo-owned duck-typed interface such as a `Protocol` or an equivalent narrow abstraction rather than an ad hoc callback surface.
That contract SHALL operate on an already-normalized snapshot plus provider-owned projection context and SHALL return provider-owned projection content/evidence for one snapshot.

Parser/shared-core flow SHALL retain ANSI stripping, newline normalization, preset resolution, surface assessment, projection fallback behavior, head/tail slicing, and final `DialogProjection`/`ProjectionMetadata` assembly around the selected processor output.

Default projection processor selection SHALL live in the provider parser, colocated with provider preset/version resolution.
That selection SHALL depend at minimum on the resolved provider parser preset/version and MAY additionally depend on matched output-variant evidence or other provider-owned snapshot evidence.
When no exact processor mapping exists for a detected provider version or output family, the provider parser SHALL follow its version-aware fallback policy rather than pushing fallback behavior into runtime lifecycle code.

Projection processor selection SHALL remain isolated from runtime lifecycle monitoring so that changing projection logic for a provider/output family does not require changing runtime `TurnMonitor` logic or unrelated provider surface-classification code.

Projection provenance SHALL identify the selected processor instance through a stable string `projector_id`.

#### Scenario: Provider swaps projection processor for a known output family
- **WHEN** a provider parser preset or output family is mapped to a different projection processor implementation
- **THEN** the provider parser uses that selected processor to produce `DialogProjection`
- **AND THEN** runtime lifecycle logic continues to consume the resulting shared projection contract without requiring unrelated changes

#### Scenario: Projection processor selection is version-aware
- **WHEN** two provider versions require different dialog-cleanup logic for otherwise similar TUI snapshots
- **THEN** the provider parser may select different projection processor instances for those versions
- **AND THEN** the selection remains inside the parser stack rather than being spread across runtime lifecycle code

#### Scenario: Projection processor fallback follows provider parser policy
- **WHEN** a detected provider version does not have an exact projection processor mapping
- **THEN** the provider parser falls back according to its version-aware selection policy
- **AND THEN** runtime lifecycle code and repo-owned helpers continue to consume the same shared projection contract

### Requirement: Shadow parser stack supports controlled projection-processor override
The runtime-owned shadow parser stack SHALL support controlled override of the projection processor used for a parsed snapshot so tests and advanced callers can swap projection behavior without rewriting provider parser classes.

This controlled override SHALL be exposed through provider parser construction and through `ShadowParserStack` construction.
The stack-level override SHALL act as pass-through injection to the selected provider parser rather than as an independent projector-selection mechanism.
This controlled override SHALL remain narrower than arbitrary runtime plugin discovery.

#### Scenario: Test or advanced caller injects a projection processor override through the shared stack
- **WHEN** a test or advanced caller supplies an explicit projection processor override through `ShadowParserStack` for a supported provider
- **THEN** the stack uses that processor for matching snapshots
- **AND THEN** the returned `DialogProjection.projection_metadata.projector_id` reflects the injected processor

#### Scenario: Direct provider parser construction supports the same explicit override
- **WHEN** a test or advanced caller constructs a provider parser directly with an explicit projection processor override
- **THEN** that parser uses the injected processor for matching snapshots
- **AND THEN** the override contract matches the shared stack pass-through behavior

### Requirement: Repo-owned shadow-aware helper code uses the shared stack-level abstraction
Repo-owned workflows or demo helpers that need to parse supported provider TUI snapshots outside the main CAO turn engine SHALL use the shared shadow parser stack or another repo-owned stack-level adapter that preserves provider selection, parser-owned projector selection, and controlled override behavior.

They SHALL NOT bypass that shared abstraction by pinning provider-private parser classes as the normal integration point for shadow parsing behavior that the stack now owns.

#### Scenario: Demo helper parses supported TUI snapshots through the shared stack
- **WHEN** a repo-owned helper needs to inspect live Claude or Codex `mode=full` output outside the main turn engine
- **THEN** it obtains parsing behavior through `ShadowParserStack` or an equivalent shared adapter
- **AND THEN** provider/version-specific projector selection remains centralized behind the shared adapter instead of being reimplemented by the helper
