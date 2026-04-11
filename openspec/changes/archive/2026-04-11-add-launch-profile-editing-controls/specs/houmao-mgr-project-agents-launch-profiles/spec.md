## ADDED Requirements

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
