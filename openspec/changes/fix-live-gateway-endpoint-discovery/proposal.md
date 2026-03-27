## Why

Attached mailbox work currently has a split discovery contract. The gateway publishes live host and port bindings in tmux session env, the mailbox runtime helper resolves only mailbox bindings, and notifier or mailbox prompts tell the agent to avoid scraping tmux state. In real runs this created an impossible flow: the agent was told to use `/v1/mail/*` but was not given a trusted way to discover the live gateway endpoint.

The current prompt hotfix works for one path, but it papers over a deeper contract flaw between gateway discovery, mailbox-runtime discovery, and gateway-first mailbox guidance. This should be fixed at the runtime-owned contract layer so future prompts, skills, and demos do not regress into port guessing or tmux scraping.

## What Changes

- Add a runtime-owned live gateway discovery contract that resolves the current attached gateway endpoint from manifest-backed session authority instead of requiring raw tmux env inspection.
- Extend the runtime-owned attached-mail resolver contract so attached mailbox work can obtain both mailbox bindings and validated live gateway mail-facade bindings from one trusted helper.
- Update gateway notifier prompts and projected mailbox system-skill guidance to rely on that runtime-owned discovery contract instead of implicit tmux knowledge or default-port guessing.
- Add regression coverage for the real failure mode where tmux session env has live gateway bindings but the provider process env snapshot does not.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: define a runtime-owned manifest-backed discovery path for validated live gateway endpoint bindings.
- `agent-gateway-mail-notifier`: require notifier wake-up prompts for shared mailbox work to remain actionable through the runtime-owned live endpoint discovery contract.
- `agent-mailbox-system-skills`: require gateway-first mailbox guidance to obtain attached mailbox and gateway action-surface bindings through runtime-owned helpers instead of split discovery channels.

## Impact

- Affected runtime modules: `src/houmao/agents/mailbox_runtime_support.py`, `src/houmao/agents/realm_controller/gateway_storage.py`, and prompt-building or validation logic under `src/houmao/agents/realm_controller/`
- Affected projected guidance: runtime-owned mailbox system-skill templates under `src/houmao/agents/realm_controller/assets/system_skills/mailbox/`
- Affected tests: gateway notifier prompt tests, mailbox-runtime resolver tests, and at least one integration or demo regression path for attached mailbox work
- Affected documentation: gateway and mailbox reference docs that currently describe live bindings and mailbox runtime resolution as separate surfaces
