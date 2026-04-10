## MODIFIED Requirements

### Requirement: `houmao-mgr agents launch` supports unified model configuration
`houmao-mgr agents launch` SHALL accept optional `--model <name>` as a one-off launch-time model override.

`houmao-mgr agents launch` SHALL also accept optional `--reasoning-level <integer>=non-negative` as a one-off launch-time tool/model-specific reasoning preset index.

Those unified launch-owned overrides SHALL be supported for both direct recipe-backed launch through `--agents` and explicit launch-profile-backed launch through `--launch-profile`.

When `--model` or `--reasoning-level` is omitted, the effective launch-owned value for that subfield MAY still come from the resolved recipe, the resolved launch profile, or a lower-precedence copied tool-native default.

Direct `--model` and `--reasoning-level` SHALL override recipe-owned and launch-profile-owned defaults without rewriting those stored reusable sources.

The launch surface SHALL NOT impose a portable `1..10` reasoning cap. Model-aware saturation or rejection semantics are handled later by the shared model-selection resolution path.

#### Scenario: Direct recipe-backed launch uses the stored source model when no override is supplied
- **WHEN** recipe `gpu-kernel-coder-codex-default` stores `launch.model: gpt-5.4`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex`
- **THEN** the resulting launch uses model `gpt-5.4`

#### Scenario: Launch-profile-backed launch uses the stored profile model when no direct override is supplied
- **WHEN** launch profile `alice` stores model override `gpt-5.4-mini`
- **AND WHEN** its source recipe stores `launch.model: gpt-5.4`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice`
- **THEN** the resulting launch uses model `gpt-5.4-mini`

#### Scenario: Direct `--model` wins over the launch-profile default
- **WHEN** launch profile `alice` stores model override `gpt-5.4-mini`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --model gpt-5.4-nano`
- **THEN** the resulting launch uses model `gpt-5.4-nano`
- **AND THEN** the stored launch profile still records `gpt-5.4-mini` as its reusable default

#### Scenario: Direct `--reasoning-level` wins over the launch-profile default
- **WHEN** launch profile `alice` stores reasoning override `2`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --reasoning-level 12`
- **THEN** the resulting launch uses launch-owned reasoning preset index `12`
- **AND THEN** the stored launch profile still records `2` as its reusable default
