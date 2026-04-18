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
- optional gateway mail-notifier appendix default

Prompt overlay SHALL support at minimum:
- `append`, which appends profile-owned prompt text after the source role prompt
- `replace`, which replaces the source role prompt with profile-owned prompt text

The gateway mail-notifier appendix default SHALL be treated as reusable birth-time launch configuration. It SHALL NOT by itself enable the notifier, set notifier mode, or set notifier interval.

#### Scenario: Launch-profile inspection reports stored birth-time defaults
- **WHEN** profile `alice` stores default agent name, workdir, auth override, model override `gpt-5.4-mini`, reasoning level `4`, mailbox config, gateway posture, and gateway mail-notifier appendix default
- **AND WHEN** an operator inspects that profile
- **THEN** the inspection output reports those stored launch defaults as profile-owned configuration
- **AND THEN** the output does not expose secret credential values inline

#### Scenario: Launch-profile stores notifier appendix without forcing notifier enablement
- **WHEN** profile `alice` stores gateway mail-notifier appendix default `Watch billing-related inbox items first.`
- **AND WHEN** an operator inspects that profile
- **THEN** the profile reports that stored appendix default
- **AND THEN** the stored profile does not imply that gateway mail-notifier polling is already enabled for future launches

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

### Requirement: Launch profiles may store memo seeds
The shared launch-profile object family SHALL support one optional memo seed as reusable birth-time launch configuration.

A memo seed SHALL support these source forms:
- inline memo text,
- one Markdown file whose content becomes `houmao-memo.md`,
- one directory shaped like the managed memo tree with optional `houmao-memo.md` and optional `pages/`.

A memo seed directory SHALL reject unsupported top-level entries outside `houmao-memo.md` and `pages/`.

The launch-profile catalog SHALL store memo seed payloads as managed content references rather than as absolute source paths.

A stored memo seed SHALL NOT store or expose an apply policy. Its launch-time behavior SHALL be source-scoped replacement of represented managed-memory components.

Launch-profile inspection SHALL report whether a memo seed is present, the seed source kind, and managed content reference metadata without printing full memo or page contents by default.

Patch mutation SHALL preserve an existing memo seed when no memo seed field is supplied. Replacement mutation SHALL clear an existing memo seed unless the replacement request supplies a new memo seed. Removing a launch profile SHALL remove the profile's catalog relationship to its memo seed.

#### Scenario: Profile stores inline memo seed text
- **WHEN** an operator creates launch profile `researcher` with inline memo seed text
- **THEN** the shared launch-profile object records a memo seed with source kind `memo`
- **AND THEN** the catalog stores the memo seed as managed content rather than as an absolute caller path
- **AND THEN** profile inspection does not report a memo seed policy

#### Scenario: Profile stores a memo-shaped seed directory
- **WHEN** an operator creates easy profile `writer` with a seed directory containing `houmao-memo.md` and `pages/style.md`
- **THEN** the shared launch-profile object records a memo seed with source kind `tree`
- **AND THEN** later profile inspection reports that a memo seed is present without printing the full contents of `pages/style.md`
- **AND THEN** profile inspection does not report a memo seed policy

#### Scenario: Patch preserves stored memo seed
- **WHEN** launch profile `reviewer` stores a memo seed and workdir `/repos/a`
- **AND WHEN** an operator patches only the workdir to `/repos/b`
- **THEN** the stored launch profile records workdir `/repos/b`
- **AND THEN** the stored memo seed remains associated with the profile

#### Scenario: Replacement clears omitted memo seed
- **WHEN** launch profile `reviewer` stores a memo seed
- **AND WHEN** an operator replaces `reviewer` in the same profile lane without supplying a memo seed
- **THEN** the replacement profile no longer records a memo seed

#### Scenario: Cross-lane replacement cannot replace memo seed owner
- **WHEN** easy profile `alice` stores a memo seed
- **AND WHEN** an operator attempts to replace `alice` through the explicit launch-profile lane
- **THEN** the replacement fails because the profile lane does not match
- **AND THEN** the easy profile and its memo seed relationship remain unchanged

### Requirement: Launch profiles may store relaunch chat-session policy
The shared launch-profile object family SHALL support an optional relaunch-only chat-session policy for future live managed-agent instances created from that profile.

The relaunch chat-session policy SHALL live under a relaunch-specific namespace and SHALL NOT affect first launch.

The policy SHALL support modes `new`, `tool_last_or_new`, and `exact`.

When the stored policy mode is `exact`, the profile SHALL store a non-empty provider-native session id.

When no relaunch chat-session policy is stored, instances launched from the profile SHALL use the system default relaunch chat-session mode `new`.

Profile inspection SHALL report the stored relaunch chat-session policy when present without exposing any credential material.

Patch mutation SHALL preserve an existing relaunch chat-session policy when no relaunch chat-session field is supplied. Replacement mutation SHALL clear an existing relaunch chat-session policy unless the replacement request supplies one.

#### Scenario: Profile stores latest-chat relaunch policy without changing first launch
- **WHEN** an operator creates launch profile `reviewer` with relaunch chat-session mode `tool_last_or_new`
- **AND WHEN** the operator launches a managed agent from `reviewer`
- **THEN** the first launch starts normally rather than resuming provider history
- **AND THEN** later relaunch of that managed agent uses the stored latest-chat relaunch policy unless a stronger relaunch command override is supplied

#### Scenario: Profile stores exact relaunch policy
- **WHEN** an operator creates launch profile `reviewer` with relaunch chat-session mode `exact` and provider session id `abc123`
- **THEN** the stored profile records the exact relaunch chat-session policy
- **AND THEN** inspection reports that exact provider session id as non-secret relaunch configuration

#### Scenario: Replacement clears omitted relaunch chat-session policy
- **WHEN** launch profile `reviewer` stores relaunch chat-session mode `tool_last_or_new`
- **AND WHEN** an operator replaces `reviewer` without supplying a relaunch chat-session policy
- **THEN** the replacement profile no longer records the prior relaunch chat-session policy

#### Scenario: Patch preserves omitted relaunch chat-session policy
- **WHEN** launch profile `reviewer` stores relaunch chat-session mode `tool_last_or_new`
- **AND WHEN** an operator patches only the profile workdir
- **THEN** the stored relaunch chat-session policy remains associated with the profile

