# managed-launch-prompt-header Specification

## Purpose
TBD - created by archiving change add-managed-prompt-header. Update Purpose after archive.
## Requirements
### Requirement: Managed launches prepend a Houmao-owned prompt header by default
Houmao-managed launch surfaces SHALL render the managed prompt header as a Houmao-owned section of the effective launch prompt by default.

That effective launch prompt SHALL be rooted at `<houmao_system_prompt>`.

When managed-header policy resolves to enabled, the rendered prompt SHALL place the managed header in a `<managed_header>` section ahead of `<prompt_body>`.

That managed prompt header SHALL:
- identify the launched agent as Houmao-managed,
- include the resolved managed-agent name and id when those identities exist for the launch,
- state that `houmao-mgr` is the canonical direct interface for interacting with the Houmao system,
- tell the agent to prefer bundled Houmao guidance and supported Houmao system interfaces for Houmao-related work,
- direct the agent toward supported manifests, runtime metadata, and service interfaces rather than unsupported ad hoc probing,
- remain general-purpose and SHALL NOT depend on naming individual packaged guidance entries.

#### Scenario: Managed launch gets the default Houmao-owned header
- **WHEN** an operator launches a managed agent through a maintained Houmao launch surface without disabling the managed header
- **THEN** the effective launch prompt is rooted at `<houmao_system_prompt>` and includes `<managed_header>` ahead of `<prompt_body>`
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
3. launch appendix append,
4. structured prompt rendering into `<houmao_system_prompt>`,
5. backend-specific prompt injection.

Within `<houmao_system_prompt>`, section order SHALL be:
1. `<managed_header>` when enabled,
2. `<prompt_body>` when body content exists.

Within `<prompt_body>`, section order SHALL be:
1. `<role_prompt>` when the source role prompt participates,
2. `<launch_profile_overlay>` when present,
3. `<launch_appendix>` when present.

When launch-profile overlay mode is `replace`, the renderer SHALL omit `<role_prompt>` from `<prompt_body>`.

For launches created after this capability is implemented, the system SHALL persist the resulting effective launch prompt together with managed-header decision metadata and structured prompt-layout metadata so later relaunch and resume can reuse one coherent launch-prompt contract.

For older managed manifests that do not already persist the structured layout metadata, managed relaunch SHALL recompute managed-header behavior using the current managed identity and the default enabled policy.

#### Scenario: Managed header renders ahead of the structured prompt body
- **WHEN** a managed launch uses a source role prompt, a launch-profile-owned prompt overlay, and a launch-owned appendix
- **AND WHEN** managed-header policy resolves to enabled
- **THEN** the effective launch prompt renders as `<houmao_system_prompt>` with `<managed_header>` before `<prompt_body>`
- **AND THEN** backend-specific prompt injection receives one composed prompt rather than a separate managed-header bootstrap message

#### Scenario: Replace overlay removes the role section from the structured prompt body
- **WHEN** a managed launch uses launch-profile overlay mode `replace`
- **AND WHEN** the operator supplies a launch-owned appendix
- **THEN** `<prompt_body>` contains `<launch_profile_overlay>` followed by `<launch_appendix>`
- **AND THEN** the rendered effective launch prompt does not also include `<role_prompt>`

#### Scenario: Relaunch of an older manifest adopts the default managed header
- **WHEN** a managed relaunch targets a pre-change manifest that lacks persisted managed-header metadata
- **AND WHEN** the relaunch does not have a stronger explicit disable override
- **THEN** the relaunched effective launch prompt is recomputed with the default managed prompt header enabled
- **AND THEN** the relaunch does not remain permanently exempt only because the original manifest predates this capability

### Requirement: Compatibility-generated launch prompts share the managed-header composition contract
When Houmao generates provider-facing launch prompts or compatibility profiles for managed launch, it SHALL derive those prompts from the same effective `<houmao_system_prompt>` composition contract used by local managed launch.

#### Scenario: Compatibility-generated profile uses the same managed header as local launch
- **WHEN** Houmao generates a provider-facing compatibility profile for a managed launch context whose managed-header policy resolves to enabled
- **AND WHEN** that launch context also includes a launch-owned appendix
- **THEN** the generated provider-facing system prompt includes the same `<houmao_system_prompt>` structure, including `<managed_header>` and `<launch_appendix>`, that local managed launch would use
- **AND THEN** compatibility launch prompt generation does not drift to a raw role-only prompt contract
