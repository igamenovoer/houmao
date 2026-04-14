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

### Requirement: Launch profiles support explicit stored mutation modes
The shared launch-profile model SHALL distinguish stored profile mutation from one-shot launch overrides.

A patch mutation SHALL update only requested stored fields and preserve unspecified stored fields.

A replacement mutation SHALL write one complete new stored profile definition for the same profile name and lane, clearing omitted optional fields back to their create defaults.

Neither patch nor replacement mutation SHALL create, stop, relaunch, or rewrite any existing live managed-agent instance.

#### Scenario: Patch preserves unspecified launch-profile defaults
- **WHEN** launch profile `alice` stores workdir `/repos/alice`, mailbox config, and prompt overlay text
- **AND WHEN** an operator patches `alice` to update only the workdir to `/repos/alice-next`
- **THEN** the stored profile records workdir `/repos/alice-next`
- **AND THEN** the stored profile still records the prior mailbox config and prompt overlay text

#### Scenario: Replacement clears omitted optional launch-profile defaults
- **WHEN** launch profile `alice` stores workdir `/repos/alice`, mailbox config, and prompt overlay text
- **AND WHEN** an operator replaces `alice` in the same profile lane while supplying only the required source and workdir `/repos/alice-next`
- **THEN** the stored profile records workdir `/repos/alice-next`
- **AND THEN** the stored profile no longer records the prior mailbox config or prompt overlay text

#### Scenario: Stored mutation does not alter live instances
- **WHEN** managed-agent instance `alice-1` was launched from launch profile `alice`
- **AND WHEN** an operator patches or replaces stored launch profile `alice`
- **THEN** the stored reusable profile is updated for future launches
- **AND THEN** live instance `alice-1` and its existing runtime manifest remain unchanged by that stored-profile mutation

### Requirement: Launch-profile replacement preserves profile lane boundaries
The shared launch-profile authoring surfaces SHALL NOT allow replacement across the easy-profile and explicit-launch-profile lanes.

When a same-name profile exists in a different lane from the requested authoring surface, replacement SHALL fail clearly before updating the stored profile.

#### Scenario: Easy replacement cannot replace explicit launch profile
- **WHEN** explicit launch profile `alice` already exists
- **AND WHEN** an operator requests same-name easy-profile replacement for `alice`
- **THEN** the replacement fails clearly because `alice` is not an easy profile
- **AND THEN** the existing explicit launch profile remains unchanged

#### Scenario: Explicit replacement cannot replace easy profile
- **WHEN** easy profile `alice` already exists
- **AND WHEN** an operator requests same-name explicit launch-profile replacement for `alice`
- **THEN** the replacement fails clearly because `alice` is not an explicit launch profile
- **AND THEN** the existing easy profile remains unchanged

### Requirement: Launch profiles may store optional persist-lane intent
Launch profiles SHALL be able to store optional persist-lane intent as one of:

- inherited persist binding,
- exact persist directory,
- disabled persist binding.

Launch profiles SHALL NOT store `memory_dir` or memory-disabled fields as the current contract.

#### Scenario: Launch profile stores exact persist directory
- **WHEN** an operator creates launch profile `alice` with `--persist-dir /shared/alice`
- **THEN** the launch profile records exact persist-lane intent for `/shared/alice`
- **AND THEN** later launches from `alice` use that value unless directly overridden

#### Scenario: Launch profile stores disabled persistence
- **WHEN** an operator creates launch profile `alice` with `--no-persist-dir`
- **THEN** the launch profile records disabled persist-lane intent
- **AND THEN** later launches from `alice` do not create a persist lane unless directly overridden

### Requirement: Launch-profile persist-lane intent participates in launch precedence
Direct `--persist-dir <path>` SHALL override profile-owned disabled persist binding or profile-owned exact persist binding.

Direct `--no-persist-dir` SHALL override any profile-owned persist configuration.

When no direct persist override is supplied, the selected launch profile's persist intent SHALL apply.

#### Scenario: Direct persist-dir overrides stored disabled persistence
- **WHEN** launch profile `alice` stores disabled persist binding
- **AND WHEN** an operator launches from `alice` with `--persist-dir /tmp/alice-persist`
- **THEN** the launch resolves persist directory `/tmp/alice-persist`
- **AND THEN** the stored profile still records disabled persist binding

#### Scenario: Stored exact persist applies without direct override
- **WHEN** launch profile `alice` stores persist directory `/shared/alice`
- **AND WHEN** an operator launches from `alice` without `--persist-dir` or `--no-persist-dir`
- **THEN** the launch resolves persist directory `/shared/alice`

