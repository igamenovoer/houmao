## Why

Attached mailbox work currently has a split discovery contract. The gateway publishes live host and port bindings in tmux session env, the provider process env snapshot may not inherit those updates, the mailbox runtime helper resolves only mailbox bindings, and notifier or mailbox prompts do not encode the actual discovery order. In real runs this created an impossible flow: the agent was told to use `/v1/mail/*` but was not given a trusted, consistent way to discover the live gateway endpoint.

The current prompt hotfix works for one path, but it papers over a deeper contract flaw between same-session env discovery, shared-registry recovery, manifest-backed authority, and gateway-first mailbox guidance. This should be fixed at the runtime-owned contract layer so future prompts, skills, and demos do not regress into port guessing, stale-env trust, or ad hoc endpoint rediscovery.

## What Changes

- Add a runtime-owned live gateway discovery contract with explicit discovery order for attached tmux-backed sessions: current process env first, then the owning tmux session env, then manifest-backed validation of the resolved live binding.
- Clarify cross-session gateway recovery so the shared registry is used to recover `runtime.manifest_path`, while the session-owned live gateway record under `<session-root>/gateway/run/current-instance.json` remains the authoritative local live-gateway record.
- Extend the runtime-owned attached-mail resolver contract so attached mailbox work can obtain both mailbox bindings and validated live gateway mail-facade bindings from one trusted helper.
- Update gateway notifier prompts and projected mailbox system-skill guidance to rely on that runtime-owned discovery contract instead of implicit tmux knowledge or default-port guessing.
- Add regression coverage for the real failure modes where tmux session env has live gateway bindings but the provider process env snapshot does not, and where out-of-process resolution must recover the session through the shared registry and manifest path.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: define the current-session and cross-session discovery order for validated live gateway endpoint bindings while keeping the manifest stable and live bindings ephemeral.
- `agent-gateway-mail-notifier`: require notifier wake-up prompts for shared mailbox work to remain actionable through the runtime-owned live endpoint discovery contract.
- `agent-mailbox-system-skills`: require gateway-first mailbox guidance to obtain attached mailbox and gateway action-surface bindings through runtime-owned helpers instead of split discovery channels.

## Impact

- Affected runtime modules: `src/houmao/agents/mailbox_runtime_support.py`, `src/houmao/agents/realm_controller/gateway_storage.py`, `src/houmao/agents/realm_controller/runtime.py`, and prompt-building or validation logic under `src/houmao/agents/realm_controller/`
- Affected projected guidance: runtime-owned mailbox system-skill templates under `src/houmao/agents/realm_controller/assets/system_skills/mailbox/`
- Affected tests: gateway notifier prompt tests, mailbox-runtime resolver tests, shared-registry or gateway-discovery tests, and at least one integration or demo regression path for attached mailbox work
- Affected documentation: gateway, mailbox, and registry reference docs that currently describe these discovery surfaces separately
