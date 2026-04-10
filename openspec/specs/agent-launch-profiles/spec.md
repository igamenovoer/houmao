## Purpose
Define reusable project-local launch-profile objects that capture birth-time launch defaults separately from source recipes and live managed-agent instances.
## Requirements
### Requirement: Launch profiles are reusable operator-owned birth-time launch definitions
The system SHALL support a shared launch-profile object family that is distinct from reusable source definitions and distinct from live managed-agent instances.

The system SHALL support two user-facing authoring lanes over that shared launch-profile model:
- easy `profile`, specialist-backed and opinionated
- explicit `launch-profile`, recipe-backed and low-level

Persisting, listing, inspecting, or removing a launch profile SHALL NOT by itself create, stop, or mutate a live managed-agent instance.

#### Scenario: Easy profile persists reusable birth-time config without creating an instance
- **WHEN** an operator creates easy profile `alice` targeting specialist `cuda-coder`
- **THEN** the system persists `alice` as reusable birth-time launch configuration
- **AND THEN** it does not create a live managed-agent instance only because the profile was created

#### Scenario: Explicit launch profile persists separately from the source recipe
- **WHEN** an operator creates explicit launch profile `nightly-ci` targeting recipe `cuda-coder-codex-default`
- **THEN** the system persists `nightly-ci` as a reusable launch-profile object
- **AND THEN** it does not clone or rewrite the referenced recipe as part of that profile creation

### Requirement: Project-local launch profiles have a stable compatibility projection
The system SHALL expose project-local launch profiles through a stable named compatibility projection under:

```text
.houmao/agents/launch-profiles/<name>.yaml
```

Catalog-backed profiles authored through either lane SHALL project into that same compatibility tree so low-level inspection and launch resolution can address one stable named resource family.

#### Scenario: Easy-authored profile projects into the launch-profile tree
- **WHEN** a project-local easy profile named `alice` exists in the authoritative catalog
- **THEN** the system materializes a compatibility resource at `.houmao/agents/launch-profiles/alice.yaml`
- **AND THEN** low-level launch-profile inspection can resolve that same named profile through the projected path

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

### Requirement: Launch profiles may store managed-header policy
The shared launch-profile object family SHALL support one optional managed-header policy as reusable birth-time launch configuration.

That stored policy SHALL support:
- `inherit`,
- `enabled`,
- `disabled`.

Launch-profile inspection payloads SHALL report the stored managed-header policy when it is present, and SHALL distinguish explicit `inherit` from an absent unsupported field.

#### Scenario: Explicit launch profile stores disabled managed-header policy
- **WHEN** an operator creates one reusable launch profile with managed-header policy `disabled`
- **THEN** the shared launch-profile object stores that policy as birth-time launch configuration
- **AND THEN** later inspection of that launch profile reports managed-header policy `disabled`

#### Scenario: Easy profile stores inherit managed-header policy
- **WHEN** an operator creates one easy profile without forcing managed-header enabled or disabled
- **THEN** the shared launch-profile object records managed-header policy `inherit`
- **AND THEN** later launch resolution can still fall through to the system default for that field

### Requirement: Launch profiles may store optional memory-directory intent
The shared launch-profile object family SHALL support optional memory-directory intent as reusable birth-time launch configuration.

At minimum, a launch profile SHALL support these memory-directory authoring outcomes:

- one explicit absolute memory directory path
- explicit disabled memory binding
- no stored memory preference

Launch-profile inspection SHALL report whether the profile stores an explicit absolute path, stores disabled memory binding, or stores no memory preference.

#### Scenario: Launch-profile inspection reports one stored exact memory directory
- **WHEN** launch profile `alice` stores memory directory `/shared/alice-memory`
- **AND WHEN** an operator inspects that launch profile
- **THEN** the inspection output reports `/shared/alice-memory` as profile-owned memory configuration
- **AND THEN** the output distinguishes that stored exact path from disabled or absent memory configuration

#### Scenario: Launch-profile inspection reports explicit disabled memory binding
- **WHEN** launch profile `alice` stores disabled memory binding
- **AND WHEN** an operator inspects that launch profile
- **THEN** the inspection output reports that the profile intentionally disables memory binding
- **AND THEN** the output distinguishes that disabled state from an absent memory preference

### Requirement: Launch-profile memory-directory intent participates in launch precedence
When a managed launch resolves effective memory binding from a launch profile, the system SHALL apply profile-owned memory-directory intent after the system default behavior and before direct launch-time overrides.

Direct `--memory-dir <path>` SHALL override profile-owned disabled memory binding or profile-owned exact-path binding.

Direct `--no-memory-dir` SHALL override any profile-owned memory configuration.

When a launch profile stores no memory preference, the effective launch SHALL fall back to the system default behavior for that launch surface.

#### Scenario: Direct exact-path override wins over a profile that disables memory
- **WHEN** launch profile `alice` stores disabled memory binding
- **AND WHEN** an operator launches from `alice` with `--memory-dir /tmp/alice-memory`
- **THEN** the resulting managed launch uses `/tmp/alice-memory` as the resolved memory directory
- **AND THEN** the stored launch profile still records disabled memory binding as its reusable default

#### Scenario: Absent profile memory configuration falls back to the system default
- **WHEN** launch profile `alice` stores no memory preference
- **AND WHEN** an operator launches from `alice` without `--memory-dir` or `--no-memory-dir`
- **THEN** the resulting managed launch resolves memory binding from the launch surface's system default behavior
- **AND THEN** the launch profile is not treated as disabling memory only because it omitted that field
