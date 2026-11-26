# Spec Delta

## ADDED Requirements

### Requirement: Operator messaging distinguishes attributed work requests, direct prompts, and CCCC chat
`houmao-operator-messaging` (`SKILL-MAIN.md` and `commands/dispatch.md`) SHALL distinguish attributed `agents single ... request` (`agent-requester` default) from verbatim `agents single ... prompt` (`agent-operator`) and separate `houmao-cccc` chat delivery from Houmao prompt and mail packets, plus `service`-mode dispatch behavior.

#### Scenario: Operator clarifies or dispatches packets across request, prompt, mail, or CCCC
- **WHEN** an operator plans or dispatches instructions to managed agents
- **THEN** `commands/dispatch.md` selects `request` vs `prompt` vs `mail` based on attribution, permission, and target mode (`tui`, `headless`, `service`, `web`)
- **AND THEN** `houmao-cccc` chat coordination is clearly distinguished from direct Houmao prompt/mail delivery

### Requirement: Operator messaging converts subcommands to a table and tightens command prose
`houmao-operator-messaging` SHALL convert the `## Subcommands` bullet list in `SKILL-MAIN.md` into a `| Subcommand | Use For | Detail |` table, remove duplication across `## Activation`, `## Help`, and `## Dispatch Model`, and tighten `commands/clarify.md` and `commands/dispatch.md` into concise checklists.

#### Scenario: Entrypoint and dispatch pages follow Imsight table structure
- **WHEN** a reviewer inspects `houmao-operator-messaging`
- **THEN** `SKILL-MAIN.md` uses a concise `## Subcommands` table with `commands/{clarify,dispatch}.md` links and zero repeated help/activation summaries

### Requirement: Operator messaging preserves clarify-first confirmation, in-chat clarify, and prompt default
`houmao-operator-messaging` SHALL preserve admin-only `## Actor Frame Gate`, routing actionable prompts without a subcommand to `clarify` (never dispatching without confirmation), keeping `clarify` strictly in-chat without writing decision files, and defaulting packets to prompt delivery (`ready-only`) unless mail is requested.

#### Scenario: Unconfirmed actionable operator input stops at clarify
- **WHEN** an admin supplies an actionable operator message without specifying `dispatch`
- **THEN** `houmao-operator-messaging` invokes `clarify()`, displays the plan table in chat without writing decision files, and waits for explicit operator confirmation before `dispatch()`
