## Why

The maintained `scripts/demo/` surface does not currently include a supported end-to-end demo for the single-agent mailbox wake-up pattern built on `houmao-mgr project easy`, even though that workflow now exists as a validated testcase and as older archived reference packs. A supported demo named `single-agent-mail-wakeup` is needed so operators and maintainers can run one canonical project-local flow from project creation through gateway notification, agent wake-up, artifact creation, and unread-mail completion without relying on legacy demo contracts.

## What Changes

- Add a new supported demo under `scripts/demo/single-agent-mail-wakeup/` for the single-agent project-easy gateway mail wake-up workflow.
- Cover two supported TUI lanes: Claude Code and Codex.
- Define the demo around a copied demo-owned project root plus a demo-owned redirected project overlay selected through `HOUMAO_PROJECT_OVERLAY_DIR`.
- Keep all generated state under the demo output root, including the copied project, redirected overlay, delivery artifacts, logs, and evidence, and ignore that generated output tree from git.
- Define the demo success contract around gateway notifier wake-up, agent-created artifact output, and actor-scoped `houmao-mgr agents mail check --unread-only` reaching zero actionable unread messages, while treating `houmao-mgr project mailbox messages list|get` as structural inspection only.
- Add the new pack to the maintained `scripts/demo/` surface so it is presented as a supported runnable demo rather than as archived legacy reference.

## Capabilities

### New Capabilities
- `single-agent-mail-wakeup-demo`: Supported single-agent demo for project-local gateway mail wake-up through `houmao-mgr project easy`, redirected project overlays, and Claude/Codex TUI lanes.

### Modified Capabilities

## Impact

- New supported demo under `scripts/demo/single-agent-mail-wakeup/`
- Demo runtime and reporting code under `src/houmao/demo/`
- Demo inputs, runner, README, and output ignore policy
- Maintained demo index in `scripts/demo/README.md`
- Reuse or adaptation of archived single-agent gateway wake-up demo concepts and helper logic
