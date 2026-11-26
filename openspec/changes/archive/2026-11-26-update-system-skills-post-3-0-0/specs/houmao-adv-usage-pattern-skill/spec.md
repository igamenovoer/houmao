# Spec Delta

## ADDED Requirements

### Requirement: Advanced usage pattern fixes v2 mail contract examples and covers CCCC and work requests
`houmao-adv-usage-pattern` SHALL fix broken v2 `/v1/mail` examples (`"schema_version": 2` -> `3` and remove `"include_body": false`) in `commands/notifier-prompt-driven-mail-loop.md`, add `houmao-cccc` push/pull/queue patterns as an explicit multi-agent coordination option, and cover `agents single request` in `pairwise-edge-loop`.

#### Scenario: Notifier mail loop example uses valid schema v3 without include_body
- **WHEN** an agent copies or adapts the `/v1/mail/{channel}/list|read|reply|archive` curl examples in `notifier-prompt-driven-mail-loop.md`
- **THEN** every request body uses `"schema_version": 3` and omits the rejected `"include_body"` field
- **AND THEN** pairwise and relay patterns distinguish `houmao-cccc` chat/queue coordination and attributed `request` from direct `prompt` and mail turns

### Requirement: Advanced usage pattern converts subcommands to a table and extracts shared pattern rules
`houmao-adv-usage-pattern` SHALL convert the `## Subcommands` bullet list in `SKILL-MAIN.md` into a clean `| Subcommand | Use For | Detail |` table, synchronize `manifest.toml` `commands` and `aliases` across all six `commands/*.md` files, and extract duplicated resend, deduplication, and ledger-table rules across 239-325 line command pages into `references/` per `imsight-agent-skill-handling`.

#### Scenario: Long loop-pattern command pages share references without duplication
- **WHEN** a reviewer inspects `houmao-adv-usage-pattern`
- **THEN** `SKILL-MAIN.md` presents a clean `## Subcommands` table and `commands/` pages reference shared resend/dedupe/ledger rules in `references/` instead of repeating them verbatim
- **AND THEN** `manifest.toml` keeps `commands = ["help", "self-notification", "notifier-prompt-driven-mail-loop", "pairwise-edge-loop", "relay-loop"]` and `aliases = ["local-close-edge-loop=pairwise-edge-loop", "pairwise edge-loop=pairwise-edge-loop", "pairwise-edge-loop-via-gateway-and-mailbox=pairwise-edge-loop", "relay-loop-via-gateway-and-mailbox=relay-loop", "self-notification-via-reminders=self-notification", "self-wakeup-via-self-mail=self-notification"]` accounting for all six `commands/*.md` files

### Requirement: Advanced usage pattern preserves layering boundary, loop topologies, and no polling
`houmao-adv-usage-pattern` SHALL preserve `## Actor Frame Gate`, its intermediate layering boundary (above direct-operation skills and below `agent-loop-lite`/`agent-loop-pro`), distinct topologies (`pairwise-edge-loop`, `relay-loop`, `notifier-prompt-driven-mail-loop`, `self-notification`), and the ban on in-chat waiting, sleeping, or polling.

#### Scenario: Coordination patterns keep distinct topologies and forbid polling
- **WHEN** an agent uses `houmao-adv-usage-pattern` to structure a pairwise, relay, or self-notification loop
- **THEN** it routes loop scaffolding outside `pro`/`lite` only for lightweight coordination and never introduces in-chat sleep or polling loops
