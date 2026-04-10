## MODIFIED Requirements

### Requirement: `project easy` surfaces support unified model configuration
`houmao-mgr project easy specialist create` SHALL accept optional `--model <name>` as a launch-owned default model selection for the created specialist.

`houmao-mgr project easy specialist create` SHALL accept optional `--reasoning-level <integer>=non-negative` as a launch-owned default reasoning preset index for the created specialist.

When supplied, those values SHALL be persisted in the specialist's launch metadata and in the generated compatibility preset as launch configuration rather than as auth-bundle content.

`houmao-mgr project easy profile create` SHALL accept optional `--model <name>` as a reusable easy-profile model override.

`houmao-mgr project easy profile create` SHALL accept optional `--reasoning-level <integer>=non-negative` as a reusable easy-profile reasoning override.

`houmao-mgr project easy instance launch` SHALL accept optional `--model <name>` and `--reasoning-level <integer>=non-negative` as one-off launch overrides for either `--specialist` or `--profile` launch.

For easy-profile-backed launch, the effective model configuration SHALL resolve with this precedence:

1. stored specialist or source recipe default
2. easy-profile model override
3. direct `project easy instance launch` override

Direct easy-instance override SHALL NOT rewrite the stored specialist or easy profile.

#### Scenario: Specialist create persists launch-owned model configuration
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool codex --api-key sk-test --model gpt-5.4 --reasoning-level 3`
- **THEN** the persisted specialist metadata records model `gpt-5.4` and reasoning level `3` as launch configuration
- **AND THEN** the generated compatibility preset records the same values under `launch`

#### Scenario: Easy profile create stores a reusable model override
- **WHEN** specialist `reviewer` already exists with source model `gpt-5.4`
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name reviewer-fast --specialist reviewer --model gpt-5.4-mini --reasoning-level 2`
- **THEN** the stored easy profile records model override `gpt-5.4-mini` and reasoning override `2`
- **AND THEN** those values are treated as easy-profile launch configuration rather than as credential state

#### Scenario: Direct easy-instance model override wins over the easy-profile default
- **WHEN** easy profile `reviewer-fast` stores model override `gpt-5.4-mini`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --name reviewer-fast-1 --model gpt-5.4-nano`
- **THEN** the resulting launch uses model `gpt-5.4-nano`
- **AND THEN** the stored easy profile still records `gpt-5.4-mini` as its reusable default

#### Scenario: Direct easy-instance reasoning override wins over the easy-profile default
- **WHEN** easy profile `reviewer-fast` stores reasoning override `2`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --profile reviewer-fast --name reviewer-fast-1 --reasoning-level 12`
- **THEN** the resulting launch uses launch-owned reasoning preset index `12`
- **AND THEN** the stored easy profile still records `2` as its reusable default
