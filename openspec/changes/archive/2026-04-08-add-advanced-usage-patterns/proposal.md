## Why

Houmao's current system-skill surface is strong for direct `houmao-mgr` commands and gateway endpoints, but it does not yet provide a supported packaged skill for higher-level multi-step usage patterns that combine mailbox, gateway, and runtime behavior. At the same time, the first desired advanced pattern, self-wakeup through self-mail plus gateway notifier polling, is invalid on the current filesystem mailbox transport because self-sent mail is seeded as read for the same actor and therefore does not stay notifier-visible.

## What Changes

- Add a new packaged system skill `houmao-adv-usage-pattern` under `src/houmao/agents/assets/system_skills/` as an index of advanced Houmao workflow compositions beyond one direct CLI or gateway action.
- Organize that skill with a top-level `SKILL.md` entry index plus separate pattern pages rather than one flattened instruction file.
- Add the first advanced pattern page for self-wakeup through gateway-mediated self-mail, where a managed agent can enqueue one or more follow-up emails to its own mailbox, leave notifier polling enabled, process those emails in later notifier-driven rounds, and stop between rounds.
- Define that pattern honestly around current contracts: mailbox unread state is the durable work backlog, gateway notifier is the live re-entry trigger, and direct gateway wakeups remain optional latency tooling rather than the durable recovery mechanism.
- Fix the filesystem mailbox transport so a self-sent message that is also delivered to the sender's own mailbox starts unread for that actor instead of being auto-marked read.
- Align gateway-backed and manager-owned mailbox send/check semantics with that self-send unread rule so filesystem self-mail remains visible to `agents mail check --unread-only` and gateway notifier polling until explicitly marked read.
- Add the new packaged skill to the maintained system-skill catalog, installation surfaces, and narrative system-skills overview documentation.

## Capabilities

### New Capabilities
- `houmao-adv-usage-pattern-skill`: packaged Houmao advanced-usage skill pages for higher-level workflow compositions, starting with self-wakeup through self-mail plus gateway notifier rounds.

### Modified Capabilities
- `agent-mailbox-fs-transport`: filesystem mailbox actor-local read-state defaults change so self-sent mail addressed to the same mailbox remains unread until explicitly marked read.
- `houmao-system-skill-installation`: packaged system-skill catalog and default install surfaces include the new `houmao-adv-usage-pattern` skill.
- `houmao-mgr-system-skills-cli`: `system-skills list|install|status` report and install the new packaged skill through the maintained catalog-driven inventory.
- `docs-system-skills-overview-guide`: the narrative overview page lists the new advanced-usage skill and explains where it fits relative to the existing direct-operation skills.

## Impact

Affected areas include `src/houmao/agents/assets/system_skills/`, `src/houmao/agents/system_skills.py`, `src/houmao/srv_ctrl/commands/system_skills.py`, `src/houmao/mailbox/managed.py`, `src/houmao/agents/realm_controller/gateway_mailbox.py`, related mailbox and gateway tests, and `docs/getting-started/system-skills-overview.md`. The public behavior change is that packaged skill inventory grows by one advanced-usage skill and filesystem self-mail becomes unread and notifier-visible until explicitly acknowledged.
