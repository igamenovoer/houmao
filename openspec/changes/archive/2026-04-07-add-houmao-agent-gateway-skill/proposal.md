## Why

Houmao now has enough gateway-specific behavior that the current skill split is no longer clean. Operators and attached agents need one packaged skill that explains gateway lifecycle, manifest-first discovery, direct gateway-only services, and reminder surfaces such as wakeups and mail-notifier without overloading `houmao-agent-messaging` or the mailbox skills.

## What Changes

- Add a packaged Houmao-owned system skill named `houmao-agent-gateway` under the maintained system-skill asset root.
- Define that skill as the gateway-focused entry point for:
  - gateway attach, detach, and status flows from outside the managed session,
  - manifest-first and live-binding discovery from inside the attached session,
  - gateway-only direct HTTP surfaces such as wakeups, notifier control, and lower-level gateway inspection,
  - boundary guidance for when callers should stay on `houmao-mgr agents ...` or `/houmao/agents/*` instead of using direct `{gateway.base_url}/v1/*`.
- Add the new packaged skill to the system-skill catalog with its own named set and include it in the managed auto-install and CLI-default selections.
- Update the `houmao-mgr system-skills` inventory and the user-facing system-skills documentation so the new gateway skill appears alongside the existing lifecycle and messaging skills.

## Capabilities

### New Capabilities
- `houmao-agent-gateway-skill`: packaged Houmao-owned system skill for gateway lifecycle, discovery, gateway-only control surfaces, and reminder services such as wakeups and mail-notifier.

### Modified Capabilities
- `houmao-system-skill-installation`: expand the packaged catalog inventory, named sets, and fixed auto-install selections to include `houmao-agent-gateway`.
- `houmao-mgr-system-skills-cli`: update list, install, and status behavior to surface the packaged gateway skill and its named set.
- `docs-readme-system-skills`: update the README system-skills overview and default-install explanation to include the new gateway skill.
- `docs-cli-reference`: update the `docs/reference/cli/system-skills.md` requirements to document the new packaged gateway skill and its boundary relative to lifecycle, messaging, and mailbox skills.

## Impact

- Affected assets under `src/houmao/agents/assets/system_skills/`, especially the packaged skill catalog and the new `houmao-agent-gateway/` directory tree.
- Affected system-skill installation and reporting behavior through `houmao.agents.system_skills` and `houmao-mgr system-skills`.
- Affected user-facing documentation for the system-skills surface in `README.md` and `docs/reference/cli/system-skills.md`.
