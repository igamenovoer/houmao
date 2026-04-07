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
- operator prompt-mode override
- durable non-secret env records
- declarative mailbox configuration
- launch posture such as headless or gateway defaults
- prompt overlay

Prompt overlay SHALL support at minimum:
- `append`, which appends profile-owned prompt text after the source role prompt
- `replace`, which replaces the source role prompt with profile-owned prompt text

#### Scenario: Launch-profile inspection reports stored birth-time defaults
- **WHEN** profile `alice` stores default agent name, workdir, auth override, mailbox config, and gateway posture
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

Live runtime mutations such as late mailbox registration SHALL remain runtime-owned and SHALL NOT rewrite the stored launch profile.

#### Scenario: Direct launch override wins over profile workdir
- **WHEN** launch profile `alice` stores working directory `/repos/alice`
- **AND WHEN** an operator launches from that profile with an explicit launch-time workdir override of `/tmp/override`
- **THEN** the launched runtime uses `/tmp/override` as the effective workdir
- **AND THEN** the stored launch profile still records `/repos/alice` as its reusable default
