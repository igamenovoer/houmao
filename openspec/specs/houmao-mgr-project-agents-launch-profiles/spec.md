# houmao-mgr-project-agents-launch-profiles Specification

## Purpose
Define the low-level `houmao-mgr internals native-agent launch-dossiers` workflow for managing native launch dossiers under `.houmao/agents/launch-profiles/`.
## Requirements
### Requirement: `houmao-mgr internals native-agent launch-dossiers` manages native launch dossiers
`houmao-mgr` SHALL expose a low-level launch-profile administration subtree shaped as:

```text
houmao-mgr internals native-agent launch-dossiers <verb>
```

At minimum, `internals native-agent launch-dossiers` SHALL expose:

- `list`
- `get`
- `add`
- `set`
- `remove`

The help text for this subtree SHALL present it as management for recipe-backed reusable birth-time launch profiles stored under `.houmao/agents/launch-profiles/`.

#### Scenario: Operator sees the internals native-agent launch-dossiers tree
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers --help`
- **THEN** the help output lists `list`, `get`, `add`, `set`, and `remove`
- **AND THEN** the help output presents `internals native-agent launch-dossiers` as management for `.houmao/agents/launch-profiles/`

### Requirement: `internals native-agent launch-dossiers` manages named explicit launch-profile resources
`houmao-mgr internals native-agent launch-dossiers add --name <profile> --recipe <recipe>` SHALL create one named explicit launch-profile resource that targets exactly one existing recipe.

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
- optional gateway mail-notifier appendix default

`launch-profiles add` SHALL accept `--model <name>` to store a reusable model override for that profile.

`launch-profiles add` SHALL accept `--reasoning-level <integer>=non-negative` to store a reusable reasoning override for that profile.

`launch-profiles add` SHALL accept `--gateway-mail-notifier-appendix-text <text>` to store a reusable notifier appendix default for that profile.

`launch-profiles set` SHALL support updating that stored model through `--model <name>` and clearing it through `--clear-model`.

`launch-profiles set` SHALL support updating the stored reasoning override through `--reasoning-level <integer>=non-negative` and clearing it through `--clear-reasoning-level`.

`launch-profiles set` SHALL support updating the stored notifier appendix default through `--gateway-mail-notifier-appendix-text <text>` and clearing it through `--clear-gateway-mail-notifier-appendix`.

`launch-profiles get --name <profile>` SHALL report the profile name, source recipe, source path, and parsed profile fields as structured output.

`launch-profiles list` SHALL enumerate existing launch-profile files and SHALL support filtering by source recipe or tool when that information is derivable from the referenced recipe.

`launch-profiles set --name <profile>` SHALL patch the named launch-profile resource without replacing unspecified advanced blocks.

`launch-profiles remove --name <profile>` SHALL delete one launch-profile resource without deleting the referenced recipe.

The explicit launch-profile surface SHALL remain recipe-backed and SHALL NOT silently assume easy-only defaults that are specific to the easy lane.

#### Scenario: Add creates an explicit launch profile with one stored model override
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name alice --recipe cuda-coder-codex-default --agent-name alice --workdir /repos/alice-cuda --model gpt-5.4-mini --reasoning-level 2`
- **THEN** the command creates `.houmao/agents/launch-profiles/alice.yaml`
- **AND THEN** the written launch profile records recipe `cuda-coder-codex-default`, managed-agent name `alice`, workdir `/repos/alice-cuda`, model override `gpt-5.4-mini`, and reasoning override `2`

#### Scenario: Add stores gateway mail-notifier appendix default
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name alice --recipe cuda-coder-codex-default --gateway-mail-notifier-appendix-text "Watch billing-related inbox items first."`
- **THEN** the created explicit launch profile stores that notifier appendix default
- **AND THEN** later `launch-profiles get --name alice` reports the stored appendix default

#### Scenario: Set patches one launch profile model without dropping advanced blocks
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with mailbox, prompt-overlay, and notifier appendix blocks
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name alice --model gpt-5.4-nano`
- **THEN** the command updates only the edited launch-profile fields
- **AND THEN** the launch profile still retains its pre-existing mailbox, prompt-overlay, and notifier appendix blocks

#### Scenario: Set can clear the stored model override
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with stored model override `gpt-5.4-mini`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name alice --clear-model`
- **THEN** the stored launch profile no longer records a profile-owned model override
- **AND THEN** later launches fall back to the source recipe or lower-precedence model source unless another override is supplied

#### Scenario: Set can clear the stored reasoning override
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with stored reasoning override `2`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name alice --clear-reasoning-level`
- **THEN** the stored launch profile no longer records a profile-owned reasoning override
- **AND THEN** later launches fall back to the source recipe or lower-precedence reasoning source unless another override is supplied

#### Scenario: Set can clear the stored notifier appendix default
- **WHEN** `.houmao/agents/launch-profiles/alice.yaml` exists with stored gateway mail-notifier appendix default
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name alice --clear-gateway-mail-notifier-appendix`
- **THEN** the stored launch profile no longer records a notifier appendix default
- **AND THEN** later launches from `alice` do not inherit a profile-owned notifier appendix unless another source supplies one

### Requirement: `internals native-agent launch-dossiers` manages explicit launch-profile managed-header policy
`houmao-mgr internals native-agent launch-dossiers add` SHALL accept:

- `--managed-header`
- `--no-managed-header`

`houmao-mgr internals native-agent launch-dossiers set` SHALL accept:

- `--managed-header`
- `--no-managed-header`
- `--clear-managed-header`

`--managed-header` and `--no-managed-header` SHALL be mutually exclusive on both surfaces.

`--clear-managed-header` SHALL clear the stored explicit policy so the profile returns to `inherit`.

`launch-profiles get --name <profile>` SHALL report the stored managed-header policy.

#### Scenario: Add stores an explicit disabled managed-header policy
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name alice --recipe cuda-coder-codex-default --no-managed-header`
- **THEN** the created explicit launch profile stores managed-header policy `disabled`
- **AND THEN** later `launch-profiles get --name alice` reports that stored policy

#### Scenario: Set clears the stored managed-header policy back to inherit
- **WHEN** explicit launch profile `alice` already stores managed-header policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name alice --clear-managed-header`
- **THEN** the stored explicit launch profile returns to managed-header policy `inherit`
- **AND THEN** later launches from `alice` fall back to the system default unless a stronger one-shot override is supplied

### Requirement: `internals native-agent launch-dossiers add --yes` replaces same-lane explicit profiles
`houmao-mgr internals native-agent launch-dossiers add --name <profile> --recipe <recipe> --yes` SHALL replace an existing same-name explicit launch profile in the active project overlay.

Replacement SHALL use create semantics: omitted optional launch defaults SHALL be cleared rather than preserved from the old profile.

When the same-name explicit launch profile already exists and replacement confirmation is not supplied, the command SHALL prompt on interactive terminals or fail in non-interactive contexts with guidance to rerun using `--yes`.

When the same-name profile exists but is not an explicit launch profile, the command SHALL fail clearly even when `--yes` is supplied.

The existing `launch-profiles set --name <profile>` command SHALL remain the patch surface for preserving unspecified advanced blocks.

#### Scenario: Explicit launch-profile add requires confirmation before replacement
- **WHEN** explicit launch profile `alice` already exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name alice --recipe reviewer-codex-default` in a non-interactive context without `--yes`
- **THEN** the command fails clearly with guidance to rerun using `--yes`
- **AND THEN** explicit launch profile `alice` remains unchanged

#### Scenario: Explicit launch-profile add yes replaces and clears omitted fields
- **WHEN** explicit launch profile `alice` targets recipe `reviewer-codex-default` and stores workdir `/repos/alice` plus prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name alice --recipe reviewer-v2-codex-default --workdir /repos/alice-v2 --yes`
- **THEN** explicit launch profile `alice` targets recipe `reviewer-v2-codex-default` and stores workdir `/repos/alice-v2`
- **AND THEN** explicit launch profile `alice` no longer stores the prior prompt overlay text

#### Scenario: Explicit launch-profile add yes rejects cross-lane conflict
- **WHEN** project profile `alice` already exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name alice --recipe reviewer-codex-default --yes`
- **THEN** the command fails clearly because `alice` is not an explicit launch profile
- **AND THEN** project profile `alice` remains unchanged

#### Scenario: Explicit launch-profile add replacement refreshes projection
- **WHEN** explicit launch profile `alice` projects to `.houmao/agents/launch-profiles/alice.yaml`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name alice --recipe reviewer-codex-default --workdir /repos/alice-next --yes`
- **THEN** the stored explicit launch profile records workdir `/repos/alice-next`
- **AND THEN** the projected `.houmao/agents/launch-profiles/alice.yaml` reflects workdir `/repos/alice-next`

### Requirement: Project launch profiles store managed-header section policy
`houmao-mgr internals native-agent launch-dossiers add` and `houmao-mgr internals native-agent launch-dossiers set` SHALL accept repeatable managed-header section policy options using `--managed-header-section SECTION=STATE`.

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

`houmao-mgr internals native-agent launch-dossiers set` SHALL also accept:

- `--clear-managed-header-section SECTION` to remove one stored section policy entry,
- `--clear-managed-header-sections` to remove all stored section policy entries.

Whole-header policy SHALL remain controlled by existing `--managed-header`, `--no-managed-header`, and `--clear-managed-header` behavior.

#### Scenario: Launch profile add stores disabled automation notice
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name alice --recipe reviewer --managed-header-section automation-notice=disabled`
- **THEN** launch profile `alice` stores automation notice section policy `disabled`
- **AND THEN** omitted identity and Houmao runtime guidance section policy remain inherited default-enabled values
- **AND THEN** omitted task reminder and mail acknowledgement section policy remain inherited default-disabled

#### Scenario: Launch profile set clears one section policy
- **WHEN** launch profile `alice` stores automation notice section policy `disabled` and identity section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name alice --clear-managed-header-section identity`
- **THEN** launch profile `alice` no longer stores an identity section policy
- **AND THEN** launch profile `alice` still stores automation notice section policy `disabled`

#### Scenario: Launch profile set clears all section policies
- **WHEN** launch profile `alice` stores one or more managed-header section policies
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name alice --clear-managed-header-sections`
- **THEN** launch profile `alice` no longer stores managed-header section policy entries
- **AND THEN** future launches from `alice` use section-default policy when the whole managed header is enabled

#### Scenario: Launch profile get reports stored section policy
- **WHEN** launch profile `alice` stores automation notice section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers get --name alice`
- **THEN** the structured output reports the stored automation notice section policy
- **AND THEN** the output does not report omitted section-default policies as stored values

#### Scenario: Launch profile add enables default-off mail acknowledgement
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name mailer --recipe reviewer --managed-header-section mail-ack=enabled`
- **THEN** launch profile `mailer` stores mail acknowledgement section policy `enabled`
- **AND THEN** future launches from `mailer` include the mail acknowledgement section when the whole managed header resolves to enabled

### Requirement: Explicit launch-profile CLI manages memo seeds
`houmao-mgr internals native-agent launch-dossiers add` SHALL accept at most one memo seed source option:
- `--memo-seed-text <text>`,
- `--memo-seed-file <path>`,
- `--memo-seed-dir <path>`.

`houmao-mgr internals native-agent launch-dossiers add` SHALL NOT accept a memo seed apply policy option.

`houmao-mgr internals native-agent launch-dossiers set` SHALL support the same source options. It SHALL also accept `--clear-memo-seed` to remove the stored memo seed from the profile.

`--clear-memo-seed` SHALL NOT be combined with a memo seed source.

`launch-profiles get --name <profile>` SHALL report memo seed presence, source kind, and managed content reference metadata without printing full memo or page contents by default.

#### Scenario: Add stores memo seed file
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name reviewer --recipe reviewer-codex-default --memo-seed-file docs/reviewer.md`
- **THEN** the command stores `docs/reviewer.md` as a profile-owned memo seed
- **AND THEN** later `launch-profiles get --name reviewer` reports memo seed source kind `memo`
- **AND THEN** later `launch-profiles get --name reviewer` does not report a memo seed policy

#### Scenario: Add rejects multiple memo seed sources
- **WHEN** an operator supplies both `--memo-seed-text` and `--memo-seed-file`
- **THEN** `launch-profiles add` fails clearly before mutating the stored profile

#### Scenario: Set replaces memo seed content
- **WHEN** launch profile `reviewer` already stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name reviewer --memo-seed-file docs/reviewer-next.md`
- **THEN** the command replaces the stored memo seed content
- **AND THEN** the profile still records no memo seed policy

#### Scenario: Memo seed policy option is unsupported
- **WHEN** an operator supplies `--memo-seed-policy replace`
- **THEN** `launch-profiles add` or `launch-profiles set` fails before mutating the stored profile

#### Scenario: Set clears memo seed
- **WHEN** launch profile `reviewer` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name reviewer --clear-memo-seed`
- **THEN** the profile no longer records a memo seed
- **AND THEN** future launches from the profile do not apply seeded memo content

#### Scenario: Directory seed rejects unsupported top-level files
- **WHEN** an operator supplies `--memo-seed-dir seed` and `seed/README.md` exists beside `seed/houmao-memo.md`
- **THEN** the command fails clearly because memo seed directories may contain only `houmao-memo.md` and `pages/` at the top level

### Requirement: `internals native-agent launch-dossiers` enforces explicit lane ownership
`houmao-mgr internals native-agent launch-dossiers list|get|set|remove` SHALL operate only on stored `launch_profile` entries even though project profiles share the same catalog-backed launch-profile family and compatibility projection path.

When `internals native-agent launch-dossiers get --name <profile>`, `set --name <profile>`, or `remove --name <profile>` targets a stored profile whose `profile_lane` is `easy_profile`, the command SHALL fail clearly instead of reading, mutating, or deleting that project profile through the explicit lane.

That wrong-lane failure SHALL identify that the named resource belongs to the project profile lane and SHALL direct the operator to the corresponding `houmao-mgr project profile <verb> --name <profile>` command.

`internals native-agent launch-dossiers list` SHALL continue returning only explicit launch-profile entries in `launch_profiles`. When that explicit-lane result is empty and one or more project profiles exist in the selected overlay, the output SHALL include operator guidance to use `houmao-mgr project profile list`.

#### Scenario: Explicit get rejects project profile with redirect guidance
- **WHEN** project profile `alice` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers get --name alice`
- **THEN** the command fails clearly instead of returning `alice`
- **AND THEN** the error explains that `alice` belongs to the project profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project profile get --name alice`

#### Scenario: Explicit set rejects project profile with redirect guidance
- **WHEN** project profile `alice` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name alice --workdir /repos/alice-next`
- **THEN** the command fails clearly before mutating `alice`
- **AND THEN** the error explains that `alice` belongs to the project profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project profile set --name alice`

#### Scenario: Explicit remove rejects project profile with redirect guidance
- **WHEN** project profile `alice` exists in the selected project overlay
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers remove --name alice`
- **THEN** the command fails clearly before deleting `alice`
- **AND THEN** the error explains that `alice` belongs to the project profile lane
- **AND THEN** the error directs the operator to `houmao-mgr project profile remove --name alice`

#### Scenario: Explicit list keeps lane filtering and adds note when only project profiles exist
- **WHEN** the selected project overlay contains one or more project profiles
- **AND WHEN** the selected project overlay contains no native launch dossiers that match the current explicit-list query
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers list`
- **THEN** the structured output reports an empty `launch_profiles` list
- **AND THEN** the structured output includes guidance to use `houmao-mgr project profile list`
- **AND THEN** the explicit list output does not inline project profiles under `launch_profiles`

### Requirement: Explicit launch profiles manage registered and private skill overlays
`houmao-mgr internals native-agent launch-dossiers add` and `houmao-mgr internals native-agent launch-dossiers set` SHALL support storing profile-owned skill overlays without mutating the referenced source recipe.

The explicit launch-profile surface SHALL accept repeatable `--add-registered-skill <name>` options. Each registered skill name SHALL reference an existing project skill registration by name and SHALL NOT create, import, copy, or symlink a new project skill registration.

The explicit launch-profile surface SHALL accept repeatable `--remove-registered-skill <name>` options on `set`. Removing a registered skill SHALL remove only that launch-profile-owned reference and SHALL NOT remove the project skill registration.

The explicit launch-profile surface SHALL accept repeatable `--add-private-skill <path>` options. Each private skill path SHALL identify a directory containing `SKILL.md`, SHALL derive its installed skill name from that directory name, and SHALL be stored with copy mode.

The explicit launch-profile surface SHALL accept repeatable `--add-private-skill-symlink <path>` options. Each private skill path SHALL identify a directory containing `SKILL.md`, SHALL derive its installed skill name from that directory name, and SHALL be stored with symlink mode.

The explicit launch-profile surface SHALL accept repeatable `--remove-private-skill <path>` options on `set`. Removing a private skill SHALL remove only the matching launch-profile-owned private skill reference and SHALL NOT mutate the referenced source directory.

Adding and removing the same registered skill name or the same normalized private skill path in one command SHALL fail clearly before mutating profile state.

Adding the same private installed skill name more than once in a single launch profile SHALL fail clearly before mutating profile state.

#### Scenario: Add stores registered and copy-mode private skills
- **WHEN** project skill `llm-wiki` is registered
- **AND WHEN** `/repo/profile-skills/audit/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name reviewer-a --recipe reviewer --add-registered-skill llm-wiki --add-private-skill /repo/profile-skills/audit`
- **THEN** explicit launch profile `reviewer-a` stores registered skill ref `llm-wiki`
- **AND THEN** it stores private skill `audit` with source path `/repo/profile-skills/audit` and mode `copy`
- **AND THEN** project skill `audit` is not added to the project skill registry

#### Scenario: Add stores symlink-mode private skill
- **WHEN** `/repo/profile-skills/live-tools/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name reviewer-a --recipe reviewer --add-private-skill-symlink /repo/profile-skills/live-tools`
- **THEN** explicit launch profile `reviewer-a` stores private skill `live-tools` with mode `symlink`
- **AND THEN** project skill `live-tools` is not added to the project skill registry

#### Scenario: Set patches registered skill refs
- **WHEN** explicit launch profile `reviewer-a` already stores registered skill ref `llm-wiki`
- **AND WHEN** project skill `project-memory` is registered
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name reviewer-a --remove-registered-skill llm-wiki --add-registered-skill project-memory`
- **THEN** explicit launch profile `reviewer-a` no longer stores registered skill ref `llm-wiki`
- **AND THEN** it stores registered skill ref `project-memory`
- **AND THEN** neither project skill registration is removed

#### Scenario: Set patches private skill refs by normalized path
- **WHEN** explicit launch profile `reviewer-a` already stores private skill source `/repo/profile-skills/audit`
- **AND WHEN** `/repo/profile-skills/audit-next/SKILL.md` exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name reviewer-a --remove-private-skill /repo/profile-skills/audit --add-private-skill /repo/profile-skills/audit-next`
- **THEN** explicit launch profile `reviewer-a` no longer stores private source `/repo/profile-skills/audit`
- **AND THEN** it stores private skill `audit-next` with source `/repo/profile-skills/audit-next`
- **AND THEN** neither source directory is deleted or imported into the project skill registry

#### Scenario: Unknown registered skill is rejected
- **WHEN** project skill `unknown-skill` is not registered
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name reviewer-a --recipe reviewer --add-registered-skill unknown-skill`
- **THEN** the command fails clearly before mutating profile state
- **AND THEN** it tells the operator that `unknown-skill` is not a registered project skill

#### Scenario: Invalid private skill path is rejected
- **WHEN** `/repo/profile-skills/bad` does not contain `SKILL.md`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name reviewer-a --recipe reviewer --add-private-skill /repo/profile-skills/bad`
- **THEN** the command fails clearly before mutating profile state
- **AND THEN** project skill `bad` is not added to the project skill registry

### Requirement: Explicit launch-profile inspection and projection report skill overlays
`houmao-mgr internals native-agent launch-dossiers get --name <profile>` SHALL report stored registered skill refs and private skill refs as part of the profile defaults.

`houmao-mgr internals native-agent launch-dossiers list` SHALL include enough structured skill-overlay summary data for operators to see that a profile contributes additional skills.

The projected `.houmao/agents/launch-profiles/<profile>.yaml` file SHALL render registered skill refs separately from private skill refs. Private skill refs SHALL include installed name, source path, and mode.

#### Scenario: Get reports registered and private skill overlays
- **WHEN** explicit launch profile `reviewer-a` stores registered skill `llm-wiki`
- **AND WHEN** it stores private skill `audit` from `/repo/profile-skills/audit` with mode `copy`
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers get --name reviewer-a`
- **THEN** the output reports registered skill ref `llm-wiki`
- **AND THEN** it reports private skill `audit`, its source path, and mode `copy`

#### Scenario: Projection renders skill overlays
- **WHEN** explicit launch profile `reviewer-a` stores registered skill `llm-wiki`
- **AND WHEN** it stores private skill `audit` from `/repo/profile-skills/audit` with mode `symlink`
- **THEN** `.houmao/agents/launch-profiles/reviewer-a.yaml` contains a launch-profile skills block with registered `llm-wiki`
- **AND THEN** that file contains private skill `audit` with source path `/repo/profile-skills/audit` and mode `symlink`

### Requirement: `internals native-agent launch-dossiers` stores explicit managed system-skill policy
`houmao-mgr internals native-agent launch-dossiers add` and `houmao-mgr internals native-agent launch-dossiers set` SHALL accept managed system-skill policy options for native launch dossiers.

The accepted options SHALL include repeatable `--system-skill-set <set>`, repeatable `--system-skill <skill>`, `--system-skills-mode inherit|extend|replace|none`, `--no-system-skills`, and the patch-only clear option `--clear-system-skills`.

When a launch-profile command receives one or more system-skill selectors without an explicit mode, it SHALL store additive mode over the source recipe policy.

`launch-profiles get --name <profile>` SHALL report stored managed system-skill policy separately from project registered/private skill overlays.

#### Scenario: Add stores additive utility skill policy
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name researcher-wiki --recipe researcher-codex-default --system-skill houmao-utils-llm-wiki`
- **THEN** the command creates an explicit launch profile with additive managed system-skill policy
- **AND THEN** the projected launch-profile YAML records that policy under profile defaults

#### Scenario: Set stores exact all policy
- **WHEN** explicit launch profile `researcher` already exists
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name researcher --system-skills-mode replace --system-skill-set all`
- **THEN** the stored launch profile records exact replacement mode with set `all`
- **AND THEN** future launches from that profile install the system-skill selection resolved from `all`

#### Scenario: Set clears stored policy back to inherit
- **WHEN** explicit launch profile `researcher` stores disabled system-skill policy
- **AND WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name researcher --clear-system-skills`
- **THEN** the stored launch profile no longer records explicit system-skill policy
- **AND THEN** future launches from that profile inherit the source recipe policy

#### Scenario: Mutually exclusive system-skill flags fail
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers set --name researcher --no-system-skills --system-skill houmao-utils-llm-wiki`
- **THEN** the command fails before updating the launch profile
- **AND THEN** the error explains that disabled mode cannot be combined with explicit system-skill selectors

### Requirement: Launch-profile templates preserve create and patch omission semantics
The launch-profile templates SHALL distinguish create-style omission from patch-style omission.

For `internals.native-agent.launch-dossiers.add`, omitted optional fields SHALL remain absent from rendered argv so the add command writes no stored value for those fields or clears them during confirmed same-lane replacement according to existing add semantics.

For `internals.native-agent.launch-dossiers.set`, omitted optional fields SHALL remain absent from rendered argv so the set command preserves existing stored values and advanced blocks.

Prompt mode SHALL only render when the intent explicitly sets prompt mode or explicitly clears prompt mode on the set surface.

Launch posture SHALL only render when the intent explicitly requests a TUI/headless posture or a template rule can determine a required posture from supplied intent.

#### Scenario: Launch-profile add omits default-sensitive fields
- **WHEN** an agent renders `internals.native-agent.launch-dossiers.add` with fields `name=alice` and `recipe=reviewer-codex-default`
- **THEN** the rendered argv includes only the required profile and recipe fields
- **AND THEN** it does not include prompt-mode, headless, managed-header, mailbox, prompt-overlay, model, or reasoning options

#### Scenario: Launch-profile set omits prompt mode during unrelated patch
- **WHEN** an agent renders `internals.native-agent.launch-dossiers.set` with fields `name=alice` and `workdir=/repos/alice-next`
- **THEN** the rendered argv includes the workdir update
- **AND THEN** it does not include prompt-mode set or clear options

#### Scenario: Explicit launch posture renders posture option
- **WHEN** an agent renders a launch-profile template with an explicit headless posture request
- **THEN** the rendered argv includes the matching launch posture option
- **AND THEN** the output reports the posture field as applied rather than inferred
