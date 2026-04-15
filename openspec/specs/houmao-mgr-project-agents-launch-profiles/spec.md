# houmao-mgr-project-agents-launch-profiles Specification

## Purpose
Define the low-level `houmao-mgr project agents launch-profiles` workflow for managing explicit recipe-backed launch profiles under `.houmao/agents/launch-profiles/`.
## Requirements
### Requirement: `houmao-mgr project agents launch-profiles` manages explicit recipe-backed launch profiles
`houmao-mgr` SHALL expose a low-level launch-profile administration subtree shaped as:

```text
houmao-mgr project agents launch-profiles <verb>
```

At minimum, `project agents launch-profiles` SHALL expose:

- `list`
- `get`
- `add`
- `set`
- `remove`

The help text for this subtree SHALL present it as management for recipe-backed reusable birth-time launch profiles stored under `.houmao/agents/launch-profiles/`.

#### Scenario: Operator sees the project agents launch-profiles tree
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles --help`
- **THEN** the help output lists `list`, `get`, `add`, `set`, and `remove`
- **AND THEN** the help output presents `project agents launch-profiles` as management for `.houmao/agents/launch-profiles/`

### Requirement: `project agents launch-profiles` manages named explicit launch-profile resources
`houmao-mgr project agents launch-profiles add --name <profile> --recipe <recipe>` SHALL create one named explicit launch-profile resource that targets exactly one existing recipe.

At minimum, launch-profile content SHALL support:
- required source recipe reference
- optional managed-agent name or id defaults
- optional working directory
- optional auth override
- optional model override by name
- optional reasoning override by non-negative preset index
- optional operator prompt-mode override
- optional durable env defaults
- optional declarative mailbox config
- optional launch posture defaults
- optional prompt overlay

`launch-profiles add` SHALL accept `--model <name>` to store a reusable model override for that profile.

`launch-profiles add` SHALL accept `--reasoning-level <integer>=non-negative` to store a reusable reasoning override for that profile.

`launch-profiles set` SHALL support updating that stored model through `--model <name>` and clearing it through `--clear-model`.

`launch-profiles set` SHALL support updating the stored reasoning override through `--reasoning-level <integer>=non-negative` and clearing it through `--clear-reasoning-level`.

`launch-profiles get --name <profile>` SHALL report the profile name, source recipe, source path, and parsed profile fields as structured output.

`launch-profiles list` SHALL enumerate existing launch-profile files and SHALL support filtering by source recipe or tool when that information is derivable from the referenced recipe.

`launch-profiles set --name <profile>` SHALL patch the named launch-profile resource without replacing unspecified advanced blocks.

`launch-profiles remove --name <profile>` SHALL delete one launch-profile resource without deleting the referenced recipe.

The explicit launch-profile surface SHALL remain recipe-backed and SHALL NOT silently assume easy-only defaults that are specific to the easy lane.

#### Scenario: Add creates an explicit launch profile with one stored model override
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe cuda-coder-codex-default --agent-name alice --workdir /repos/alice-cuda --model gpt-5.4-mini --reasoning-level 2`
- **THEN** the command creates `.houmao/agents/launch-profiles/alice.yaml`
- **AND THEN** the written launch profile records recipe `cuda-coder-codex-default`, managed-agent name `alice`, workdir `/repos/alice-cuda`, model override `gpt-5.4-mini`, and reasoning override `2`

#### Scenario: Set patches one launch profile model without dropping advanced blocks
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with mailbox and prompt-overlay blocks
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --model gpt-5.4-nano`
- **THEN** the command updates only the edited launch-profile fields
- **AND THEN** the launch profile still retains its pre-existing mailbox and prompt-overlay blocks

#### Scenario: Set can clear the stored model override
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with stored model override `gpt-5.4-mini`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-model`
- **THEN** the stored launch profile no longer records a profile-owned model override
- **AND THEN** later launches fall back to the source recipe or lower-precedence model source unless another override is supplied

#### Scenario: Set can clear the stored reasoning override
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with stored reasoning override `2`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-reasoning-level`
- **THEN** the stored launch profile no longer records a profile-owned reasoning override
- **AND THEN** later launches fall back to the source recipe or lower-precedence reasoning source unless another override is supplied

### Requirement: `project agents launch-profiles` manages explicit launch-profile managed-header policy
`houmao-mgr project agents launch-profiles add` SHALL accept:

- `--managed-header`
- `--no-managed-header`

`houmao-mgr project agents launch-profiles set` SHALL accept:

- `--managed-header`
- `--no-managed-header`
- `--clear-managed-header`

`--managed-header` and `--no-managed-header` SHALL be mutually exclusive on both surfaces.

`--clear-managed-header` SHALL clear the stored explicit policy so the profile returns to `inherit`.

`launch-profiles get --name <profile>` SHALL report the stored managed-header policy.

#### Scenario: Add stores an explicit disabled managed-header policy
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe cuda-coder-codex-default --no-managed-header`
- **THEN** the created explicit launch profile stores managed-header policy `disabled`
- **AND THEN** later `launch-profiles get --name alice` reports that stored policy

#### Scenario: Set clears the stored managed-header policy back to inherit
- **WHEN** explicit launch profile `alice` already stores managed-header policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-managed-header`
- **THEN** the stored explicit launch profile returns to managed-header policy `inherit`
- **AND THEN** later launches from `alice` fall back to the system default unless a stronger one-shot override is supplied

### Requirement: Launch-profile auth overrides track auth profile identity across auth rename
Stored explicit launch-profile auth overrides SHALL resolve through auth profile identity rather than using auth display-name text as the authoritative relationship key.

When a launch profile selects an auth override, the stored relationship SHALL remain valid after that auth profile is renamed.

Operator-facing launch-profile inspection SHALL render the current auth display name for the referenced auth profile.

#### Scenario: Launch-profile auth override survives auth rename
- **WHEN** explicit launch profile `alice` stores an auth override referencing one Codex auth profile named `work`
- **AND WHEN** that auth profile is renamed to `breakglass`
- **THEN** later launch from profile `alice` still resolves the same auth profile
- **AND THEN** the operator does not need to edit `alice` only because the auth display name changed

#### Scenario: Launch-profile get renders the current auth display name
- **WHEN** explicit launch profile `alice` references one auth profile whose current display name is `breakglass`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles get --name alice`
- **THEN** the command reports auth override `breakglass`
- **AND THEN** it does not require the caller to know the internal auth profile id or opaque bundle reference

### Requirement: `project agents launch-profiles add --yes` replaces same-lane explicit profiles
`houmao-mgr project agents launch-profiles add --name <profile> --recipe <recipe> --yes` SHALL replace an existing same-name explicit launch profile in the active project overlay.

Replacement SHALL use create semantics: omitted optional launch defaults SHALL be cleared rather than preserved from the old profile.

When the same-name explicit launch profile already exists and replacement confirmation is not supplied, the command SHALL prompt on interactive terminals or fail in non-interactive contexts with guidance to rerun using `--yes`.

When the same-name profile exists but is not an explicit launch profile, the command SHALL fail clearly even when `--yes` is supplied.

The existing `launch-profiles set --name <profile>` command SHALL remain the patch surface for preserving unspecified advanced blocks.

#### Scenario: Explicit launch-profile add requires confirmation before replacement
- **WHEN** explicit launch profile `alice` already exists
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe reviewer-codex-default` in a non-interactive context without `--yes`
- **THEN** the command fails clearly with guidance to rerun using `--yes`
- **AND THEN** explicit launch profile `alice` remains unchanged

#### Scenario: Explicit launch-profile add yes replaces and clears omitted fields
- **WHEN** explicit launch profile `alice` targets recipe `reviewer-codex-default` and stores workdir `/repos/alice` plus prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe reviewer-v2-codex-default --workdir /repos/alice-v2 --yes`
- **THEN** explicit launch profile `alice` targets recipe `reviewer-v2-codex-default` and stores workdir `/repos/alice-v2`
- **AND THEN** explicit launch profile `alice` no longer stores the prior prompt overlay text

#### Scenario: Explicit launch-profile add yes rejects cross-lane conflict
- **WHEN** easy profile `alice` already exists
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe reviewer-codex-default --yes`
- **THEN** the command fails clearly because `alice` is not an explicit launch profile
- **AND THEN** easy profile `alice` remains unchanged

#### Scenario: Explicit launch-profile add replacement refreshes projection
- **WHEN** explicit launch profile `alice` projects to `.houmao/agents/launch-profiles/alice.yaml`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe reviewer-codex-default --workdir /repos/alice-next --yes`
- **THEN** the stored explicit launch profile records workdir `/repos/alice-next`
- **AND THEN** the projected `.houmao/agents/launch-profiles/alice.yaml` reflects workdir `/repos/alice-next`

### Requirement: Project launch profiles store managed-header section policy
`houmao-mgr project agents launch-profiles add` and `houmao-mgr project agents launch-profiles set` SHALL accept repeatable managed-header section policy options using `--managed-header-section SECTION=STATE`.

Supported `SECTION` values SHALL include:

- `identity`
- `houmao-runtime-guidance`
- `automation-notice`
- `task-reminder`
- `mail-ack`

Supported `STATE` values SHALL include:

- `enabled`
- `disabled`

The stored section policy SHALL apply only to the named section. Omitted sections SHALL inherit the section default.

`houmao-mgr project agents launch-profiles set` SHALL also accept:

- `--clear-managed-header-section SECTION` to remove one stored section policy entry,
- `--clear-managed-header-sections` to remove all stored section policy entries.

Whole-header policy SHALL remain controlled by existing `--managed-header`, `--no-managed-header`, and `--clear-managed-header` behavior.

#### Scenario: Launch profile add stores disabled automation notice
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name alice --recipe reviewer --managed-header-section automation-notice=disabled`
- **THEN** launch profile `alice` stores automation notice section policy `disabled`
- **AND THEN** omitted identity and Houmao runtime guidance section policy remain inherited default-enabled values
- **AND THEN** omitted task reminder and mail acknowledgement section policy remain inherited default-disabled

#### Scenario: Launch profile set clears one section policy
- **WHEN** launch profile `alice` stores automation notice section policy `disabled` and identity section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-managed-header-section identity`
- **THEN** launch profile `alice` no longer stores an identity section policy
- **AND THEN** launch profile `alice` still stores automation notice section policy `disabled`

#### Scenario: Launch profile set clears all section policies
- **WHEN** launch profile `alice` stores one or more managed-header section policies
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles set --name alice --clear-managed-header-sections`
- **THEN** launch profile `alice` no longer stores managed-header section policy entries
- **AND THEN** future launches from `alice` use section-default policy when the whole managed header is enabled

#### Scenario: Launch profile get reports stored section policy
- **WHEN** launch profile `alice` stores automation notice section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr project agents launch-profiles get --name alice`
- **THEN** the structured output reports the stored automation notice section policy
- **AND THEN** the output does not report omitted section-default policies as stored values

#### Scenario: Launch profile add enables default-off mail acknowledgement
- **WHEN** an operator runs `houmao-mgr project agents launch-profiles add --name mailer --recipe reviewer --managed-header-section mail-ack=enabled`
- **THEN** launch profile `mailer` stores mail acknowledgement section policy `enabled`
- **AND THEN** future launches from `mailer` include the mail acknowledgement section when the whole managed header resolves to enabled

