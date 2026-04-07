## MODIFIED Requirements

### Requirement: Launch profiles capture durable birth-time launch defaults
Launch profiles SHALL support durable birth-time launch defaults without embedding secrets inline.

At minimum, the shared model SHALL support:
- source reference
- managed-agent identity defaults
- working directory
- auth override by reference
- model override by name
- normalized reasoning override by level `1..10`
- operator prompt-mode override
- durable non-secret env records
- declarative mailbox configuration
- launch posture such as headless or gateway defaults
- prompt overlay

Prompt overlay SHALL support at minimum:
- `append`, which appends profile-owned prompt text after the source role prompt
- `replace`, which replaces the source role prompt with profile-owned prompt text

#### Scenario: Launch-profile inspection reports stored birth-time defaults
- **WHEN** profile `alice` stores default agent name, workdir, auth override, model override `gpt-5.4-mini`, reasoning level `4`, mailbox config, and gateway posture
- **AND WHEN** an operator inspects that profile
- **THEN** the inspection output reports those stored launch defaults as profile-owned configuration
- **AND THEN** the output does not expose secret credential values inline

### Requirement: Launch-profile resolution applies explicit precedence
The system SHALL resolve effective launch inputs with this precedence order:

1. tool-adapter defaults
2. source recipe defaults
3. launch-profile defaults
4. direct CLI launch overrides
5. live runtime mutations

Fields omitted by a higher-priority layer SHALL survive from the next lower-priority layer.

Live runtime mutations such as late mailbox registration or in-session model switching SHALL remain runtime-owned and SHALL NOT rewrite the stored launch profile.

#### Scenario: Direct launch override wins over profile workdir
- **WHEN** launch profile `alice` stores working directory `/repos/alice`
- **AND WHEN** an operator launches from that profile with an explicit launch-time workdir override of `/tmp/override`
- **THEN** the launched runtime uses `/tmp/override` as the effective workdir
- **AND THEN** the stored launch profile still records `/repos/alice` as its reusable default

#### Scenario: Direct launch model override wins over profile model
- **WHEN** source recipe `alice-coder` stores default model `gpt-5.4`
- **AND WHEN** launch profile `alice` stores model override `gpt-5.4-mini`
- **AND WHEN** an operator launches from that profile with direct override `--model gpt-5.4-nano`
- **THEN** the launched runtime uses `gpt-5.4-nano` as the effective model
- **AND THEN** the stored launch profile still records `gpt-5.4-mini` as its reusable default

#### Scenario: Direct launch reasoning override wins over profile reasoning
- **WHEN** source recipe `alice-coder` stores default reasoning level `6`
- **AND WHEN** launch profile `alice` stores reasoning override `4`
- **AND WHEN** an operator launches from that profile with direct override `--reasoning-level 9`
- **THEN** the launched runtime uses reasoning level `9` as the effective launch-owned value
- **AND THEN** the stored launch profile still records `4` as its reusable default
