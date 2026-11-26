# Spec Delta

## ADDED Requirements

### Requirement: Agent access covers self-key lifecycle, detached default-group, and immediate admission feedback
`houmao-agent-access` SHALL document `agents single ... access self-key {rotate|revoke}`, `access default-group set --passive-url`, `access list` roster/default inspection, grant/revoke stderr immediate-admission feedback, the six built-in groups (`agent-observer`..`agent-admin`, `managed-self`), and exact-resource role templates.

#### Scenario: Owner or peer inspects default group, rotates self-key, or applies role templates
- **WHEN** an owner sets `default-group` on a detached target, rotates a `managed-self` key, or creates a scoped mount/plugin role
- **THEN** `commands/policy.md` and `SKILL-MAIN.md` cover `self-key {rotate|revoke}`, `--passive-url`, `access list`, stderr admission feedback, all six built-in groups, and `--template --resource`

### Requirement: Agent access fixes policy.md formatting, replaces informal names, and normalizes subcommand table
`houmao-agent-access` SHALL fix the missing blank line before `## Built-In Groups and the Default` at `commands/policy.md:47`, replace informal `"Bob/Alice"` prose with neutral operator/caller/target terminology, and remove `()` from the `Subcommand` column of `SKILL-MAIN.md`'s `## Subcommands` table (`help`, `provision`, etc.).

#### Scenario: Formatting and terminology match suite-wide standards
- **WHEN** a reviewer inspects `houmao-agent-access/SKILL-MAIN.md` and `commands/policy.md`
- **THEN** `commands/policy.md` has clean Markdown spacing before headings and neutral caller/target wording
- **AND THEN** `SKILL-MAIN.md` `## Subcommands` uses bare subcommand names in the `Subcommand` column while keeping `X->cmd()` syntax in prose designators

### Requirement: Agent access preserves authority separation, roster transitions, rotation order, and secret safety
`houmao-agent-access` SHALL preserve `## Actor Frame Gate`, authority separation (execution owner, live admin, managed peer, operator), empty-roster open mode vs keyed mode, enrolling replacement admin key before revoking sole admin key, and non-disclosure of private keys, proofs, or owner-private files, plus `references/access-scope.md`.

#### Scenario: Sole administrator rotation preserves keyed mode without leaking keys
- **WHEN** an operator rotates the sole administrator key in `houmao-agent-access`
- **THEN** the workflow enrolls and qualifies the replacement key before revoking the old key and never prints private keys or proof material
