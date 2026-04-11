## ADDED Requirements

### Requirement: `project easy profile set` patches specialist-backed easy profiles
`houmao-mgr project easy profile set --name <profile>` SHALL patch one existing specialist-backed easy profile in the active project overlay.

The command SHALL preserve the profile source specialist and SHALL preserve unspecified stored launch defaults.

At minimum, `project easy profile set` SHALL support the same stored launch-default field families as `project agents launch-profiles set`, including managed-agent identity defaults, workdir, auth, memory binding, model, reasoning level, prompt mode, env records, mailbox config, launch posture, managed-header policy, and prompt overlay.

The command SHALL expose clear flags for nullable or collection fields where the explicit launch-profile `set` surface already exposes matching clear behavior.

When no requested update or clear flag is supplied, the command SHALL fail clearly without rewriting the profile.

#### Scenario: Easy profile set updates auth without dropping prompt overlay
- **WHEN** easy profile `alice` targets specialist `reviewer` and stores auth override `work` plus prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --auth breakglass`
- **THEN** easy profile `alice` stores auth override `breakglass`
- **AND THEN** easy profile `alice` still stores its prior prompt overlay text

#### Scenario: Easy profile set clears prompt overlay
- **WHEN** easy profile `alice` stores prompt overlay mode `append` with prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --clear-prompt-overlay`
- **THEN** easy profile `alice` no longer stores prompt overlay mode or prompt overlay text
- **AND THEN** future launches from `alice` fall back to the source specialist prompt unless a stronger launch-time prompt override is supplied

#### Scenario: Easy profile set rejects empty update
- **WHEN** easy profile `alice` exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice` without any update or clear flags
- **THEN** the command fails clearly
- **AND THEN** easy profile `alice` remains unchanged

### Requirement: `project easy profile create --yes` replaces same-lane profiles
`houmao-mgr project easy profile create --name <profile> --specialist <specialist> --yes` SHALL replace an existing same-name easy profile in the active project overlay.

Replacement SHALL use create semantics: omitted optional launch defaults SHALL be cleared rather than preserved from the old profile.

When the same-name easy profile already exists and replacement confirmation is not supplied, the command SHALL prompt on interactive terminals or fail in non-interactive contexts with guidance to rerun using `--yes`.

When the same-name profile exists but is not an easy profile, the command SHALL fail clearly even when `--yes` is supplied.

#### Scenario: Easy profile create requires confirmation before replacement
- **WHEN** easy profile `alice` already exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist reviewer` in a non-interactive context without `--yes`
- **THEN** the command fails clearly with guidance to rerun using `--yes`
- **AND THEN** easy profile `alice` remains unchanged

#### Scenario: Easy profile create yes replaces and clears omitted fields
- **WHEN** easy profile `alice` targets specialist `reviewer` and stores workdir `/repos/alice` plus prompt overlay text
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist reviewer-v2 --workdir /repos/alice-v2 --yes`
- **THEN** easy profile `alice` targets specialist `reviewer-v2` and stores workdir `/repos/alice-v2`
- **AND THEN** easy profile `alice` no longer stores the prior prompt overlay text

#### Scenario: Easy profile create yes rejects cross-lane conflict
- **WHEN** explicit launch profile `alice` already exists
- **AND WHEN** an operator runs `houmao-mgr project easy profile create --name alice --specialist reviewer --yes`
- **THEN** the command fails clearly because `alice` is not an easy profile
- **AND THEN** explicit launch profile `alice` remains unchanged

### Requirement: Easy-profile mutation refreshes the compatibility projection
After `project easy profile set` or same-lane `project easy profile create --yes` replacement updates stored profile state, the command SHALL rematerialize the project agent catalog projection.

The projected `.houmao/agents/launch-profiles/<profile>.yaml` resource SHALL reflect the updated stored profile.

#### Scenario: Easy profile set updates projected launch profile
- **WHEN** easy profile `alice` projects to `.houmao/agents/launch-profiles/alice.yaml`
- **AND WHEN** an operator runs `houmao-mgr project easy profile set --name alice --workdir /repos/alice-next`
- **THEN** the stored easy profile records workdir `/repos/alice-next`
- **AND THEN** the projected `.houmao/agents/launch-profiles/alice.yaml` reflects workdir `/repos/alice-next`
