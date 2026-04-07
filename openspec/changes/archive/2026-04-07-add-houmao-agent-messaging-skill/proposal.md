## Why

Houmao already exposes several ways to communicate with managed agents, including normal prompt turns, interrupts, queued gateway requests, raw `send-keys`, mailbox follow-up, and pair-managed HTTP routes. But the packaged Houmao-owned system-skill set does not currently include one canonical skill that explains how to choose between those paths, so both managed agents and external operators lack a single messaging/control entry point.

## What Changes

- Add a new packaged Houmao-owned system skill named `houmao-agent-messaging`.
- Scope that skill to communication with already-existing Houmao-managed agents across:
  - synchronous prompt turns through `houmao-mgr agents prompt`
  - transport-neutral interrupts through `houmao-mgr agents interrupt`
  - queued gateway control through `houmao-mgr agents gateway prompt|interrupt`
  - raw control input through `houmao-mgr agents gateway send-keys`
  - mailbox follow-up through `houmao-mgr agents mail resolve-live|status|check|send|reply|mark-read`
  - managed-agent HTTP routes under `/houmao/agents/*`, plus direct gateway HTTP only when the lower-level route is the right current surface
- Make the packaged skill teach discovery and path selection based on target identity, live gateway availability, mailbox capability, and the caller's intent such as normal conversation, queueing work, raw terminal control, mailbox messaging, or context reset.
- Cover clear-context and chat-session reset guidance as part of the messaging surface by documenting the existing gateway control APIs honestly, including when a current `houmao-mgr` flag does not yet exist for that action.
- Keep launch, join, stop, relaunch, cleanup, specialist CRUD, and mailbox transport internals out of scope for the new skill.
- Reuse the existing Houmao mailbox skills for transport-specific mailbox behavior instead of duplicating filesystem or Stalwart operational detail inside the new skill.
- Add the new packaged skill to the system-skill catalog and default install selections used by managed launch, managed join, and CLI-default external installs.
- Update README and CLI reference docs to describe the new packaged messaging skill and the expanded default skill set.

## Capabilities

### New Capabilities
- `houmao-agent-messaging-skill`: Packaged Houmao-owned messaging/control skill that routes prompt, interrupt, gateway, raw-input, mailbox, and reset-context workflows for Houmao-managed agents.

### Modified Capabilities
- `houmao-system-skill-installation`: The packaged system-skill catalog and fixed auto-install set lists include the new messaging skill and its default-install coverage.
- `houmao-mgr-system-skills-cli`: `system-skills list|install|status` reflect the new messaging skill and the updated default selection outcome.
- `docs-cli-reference`: CLI reference docs describe the packaged messaging skill, its communication-path boundary, and the revised default skill inventory.
- `docs-readme-system-skills`: The README system-skills overview lists the new packaged messaging skill and the current default install behavior.

## Impact

- Affected code: `src/houmao/agents/assets/system_skills/`, `src/houmao/agents/system_skills.py`, `src/houmao/agents/assets/system_skills/catalog.toml`
- Affected docs: `README.md`, `docs/reference/cli/system-skills.md`, and related CLI reference pages
- Affected tests: system-skill catalog/installer tests and `houmao-mgr system-skills` CLI tests
