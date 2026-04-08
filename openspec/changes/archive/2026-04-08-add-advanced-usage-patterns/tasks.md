## 1. Advanced Skill Package

- [x] 1.1 Create the packaged `houmao-adv-usage-pattern` system-skill asset directory with `SKILL.md`, tool interface metadata, and a first pattern page for self-wakeup through self-mail plus notifier-driven rounds.
- [x] 1.2 Write the self-wakeup pattern page so it composes `houmao-agent-email-comms`, `houmao-agent-gateway`, and `houmao-process-emails-via-gateway` and states the mailbox/notifier/wakeup durability boundaries correctly.
- [x] 1.3 Update existing mailbox skill references that currently describe self-notification so they point at or align with the new advanced-usage skill instead of restating stale behavior.

## 2. Catalog, CLI, And Overview Exposure

- [x] 2.1 Add `houmao-adv-usage-pattern` to the packaged system-skill catalog with a dedicated named set and include that set in managed launch, managed join, and CLI-default selections.
- [x] 2.2 Update system-skill inventory and installation reporting surfaces so `houmao-mgr system-skills list|install|status` expose the new advanced-usage skill through the catalog-driven inventory.
- [x] 2.3 Update `docs/getting-started/system-skills-overview.md` to list the new advanced-usage skill and explain how it relates to the existing direct-operation skills.

## 3. Filesystem Self-Mail Unread Semantics

- [x] 3.1 Change filesystem mailbox delivery initialization so a mailbox that is among the delivered recipients starts unread even when that same mailbox is also the sender.
- [x] 3.2 Apply the same self-addressed unread rule to mailbox-state repair, rebuild, and lazy mailbox-local state initialization paths so reconstructed state matches fresh delivery semantics.
- [x] 3.3 Align filesystem gateway-backed and manager-owned mailbox send or reply result shaping with the effective actor-local unread state for self-addressed mail.

## 4. Validation

- [x] 4.1 Add unit tests for filesystem self-send actor state, including fresh delivery and any repaired or lazily initialized mailbox-local state paths that synthesize defaults.
- [x] 4.2 Add gateway or managed-agent mailbox tests that confirm self-sent filesystem mail appears in `check --unread-only`, remains notifier-visible until explicit mark-read, and becomes read only after successful acknowledgement.
- [x] 4.3 Add or update system-skill catalog, CLI inventory, and documentation-facing tests or assertions so the new advanced-usage skill is covered by the maintained packaged inventory surface.
