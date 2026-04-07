## ADDED Requirements

### Requirement: Managed launches prepend a Houmao-owned prompt header by default
Houmao-managed launch surfaces SHALL prepend a Houmao-owned managed prompt header to the effective launch prompt by default.

That managed prompt header SHALL:
- identify the launched agent as Houmao-managed,
- include the resolved managed-agent name and id when those identities exist for the launch,
- state that `houmao-mgr` is the canonical direct interface for interacting with the Houmao system,
- tell the agent to prefer bundled Houmao guidance and supported Houmao system interfaces for Houmao-related work,
- direct the agent toward supported manifests, runtime metadata, and service interfaces rather than unsupported ad hoc probing,
- remain general-purpose and SHALL NOT depend on naming individual packaged guidance entries.

#### Scenario: Managed launch gets the default Houmao-owned header
- **WHEN** an operator launches a managed agent through a maintained Houmao launch surface without disabling the managed header
- **THEN** the effective launch prompt starts with the Houmao-owned managed prompt header
- **AND THEN** that header identifies the agent as Houmao-managed and names `houmao-mgr` as the canonical direct Houmao interface

### Requirement: Managed-header policy resolves through launch override, profile policy, and default
The managed prompt header SHALL resolve through this precedence order:

1. explicit one-shot launch override,
2. stored launch-profile policy when present,
3. system default.

The system default for this capability SHALL be enabled.

Stored launch-profile policy SHALL support the three states:
- inherit,
- enabled,
- disabled.

#### Scenario: Direct disable wins over stored enabled policy
- **WHEN** a reusable launch profile stores managed-header policy `enabled`
- **AND WHEN** an operator launches from that profile with an explicit one-shot disable override
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** the stored launch profile still records policy `enabled`

#### Scenario: Stored disabled policy wins when no direct override is supplied
- **WHEN** a reusable launch profile stores managed-header policy `disabled`
- **AND WHEN** an operator launches from that profile without any direct managed-header override
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** the launch does not silently fall back to the default enabled behavior

### Requirement: Managed header participates in effective launch-prompt composition
When managed-header policy resolves to enabled, the system SHALL treat the managed prompt header as part of the effective launch prompt rather than as a separate bootstrap-only prompt.

Prompt composition order SHALL be:

1. source role prompt,
2. launch-profile prompt overlay resolution,
3. managed prompt header prepend,
4. backend-specific prompt injection.

For launches created after this capability is implemented, the system SHALL persist the resulting effective launch prompt and managed-header decision metadata so later relaunch and resume can reuse one coherent launch-prompt contract.

For older managed manifests that do not already persist managed-header metadata, managed relaunch SHALL recompute managed-header behavior using the current managed identity and the default enabled policy.

#### Scenario: Managed header is prepended after prompt overlay resolution
- **WHEN** a managed launch uses a source role prompt and a launch-profile-owned prompt overlay
- **AND WHEN** managed-header policy resolves to enabled
- **THEN** the effective launch prompt reflects the already-resolved overlay result with the managed prompt header prepended ahead of it
- **AND THEN** backend-specific prompt injection receives one composed prompt rather than a separate managed-header bootstrap message

#### Scenario: Relaunch of an older manifest adopts the default managed header
- **WHEN** a managed relaunch targets a pre-change manifest that lacks persisted managed-header metadata
- **AND WHEN** the relaunch does not have a stronger explicit disable override
- **THEN** the relaunched effective launch prompt is recomputed with the default managed prompt header enabled
- **AND THEN** the relaunch does not remain permanently exempt only because the original manifest predates this capability

### Requirement: Compatibility-generated launch prompts share the managed-header composition contract
When Houmao generates provider-facing launch prompts or compatibility profiles for managed launch, it SHALL derive those prompts from the same effective launch-prompt composition contract used by local managed launch.

#### Scenario: Compatibility-generated profile uses the same managed header as local launch
- **WHEN** Houmao generates a provider-facing compatibility profile for a managed launch context whose managed-header policy resolves to enabled
- **THEN** the generated provider-facing system prompt includes the same Houmao-owned managed prompt header that local managed launch would use
- **AND THEN** compatibility launch prompt generation does not drift to a raw role-only prompt contract
