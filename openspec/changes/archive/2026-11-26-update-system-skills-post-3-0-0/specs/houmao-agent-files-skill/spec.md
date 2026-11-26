# Spec Delta

## ADDED Requirements

### Requirement: Agent files aligns existing skills and mcp mounts and --when-idle with role templates and signer hints
`houmao-agent-files` (`references/mount-scope.md` and `commands/publish.md`) SHALL preserve and align its existing `skills` (`managed_web_skills`) and `mcp` (`managed_web_mcp`/`mcp_servers`) logical mount coverage and self-only `agents self files push --when-idle` recovery guidance with the built-in `agent-maintainer` group, exact-resource role templates (`skill-reviewer`, `skill-editor`, `skill-publisher`, `skill-maintainer`), and mode-aware (`open` vs `keyed`) signer hints.

#### Scenario: File edits align mounts and busy-push recovery with role templates and signer hints
- **WHEN** a caller inspects mounts or pushes committed edits while a DSH Web target is busy
- **THEN** `references/mount-scope.md` preserves `skills` (`managed_web_skills`) and `mcp` (`managed_web_mcp` with `mcp_servers`) mount coverage and explains built-in `agent-maintainer` vs `skill-reviewer`, `skill-editor`, `skill-publisher`, and `skill-maintainer` templates plus `open` vs `keyed` signer selection
- **AND THEN** `commands/publish.md` preserves self-only `agents self files push --when-idle` recovery for busy targets alongside mode-aware signer hints without dropping `--expected-base` or `--operation-id`

### Requirement: Agent files adds explicit Helper Subcommands line and normalizes table parentheses
`houmao-agent-files/SKILL-MAIN.md` SHALL add an explicit `### Helper Subcommands` subsection stating `No helper subcommands are currently exposed.` per `imsight-agent-skill-handling` and remove `()` from the `Subcommand` column in `## Subcommands` tables (`discover`, `inspect`, `edit-draft`, `publish`, `reconcile`, `help`).

#### Scenario: Complex-procedure three-split and table format are strictly compliant
- **WHEN** a reviewer checks `houmao-agent-files/SKILL-MAIN.md` against `imsight-agent-skill-handling`
- **THEN** `## Subcommands` contains `### Procedural Subcommands`, `### Helper Subcommands` (`No helper subcommands are currently exposed.`), and `### Misc Subcommands` with bare command names in table columns

### Requirement: Agent files preserves mount exclusivity, lease capability security, lifecycle separation, and reconcile
`houmao-agent-files` SHALL preserve `## Actor Frame Gate`, no direct target-filesystem fallback, lease exclusivity, 2 MiB decoded write limit, `umask 077` `lease_capability` file handling, draft!=commit!=publish!=refresh separation, `reconcile` by original `operation_id` on uncertain push, and `references/{mount-scope,receipts}.md`.

#### Scenario: Uncertain push reconciles without replay and anonymous lease keeps capability private
- **WHEN** a push status is uncertain or an anonymous lease is opened
- **THEN** `houmao-agent-files` stores `lease_capability` in an owner-private `umask 077` file for `--lease-capability-file` and reconciles uncertain pushes by `operation_id` without replaying
