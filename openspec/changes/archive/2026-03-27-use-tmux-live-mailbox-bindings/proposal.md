## Why

Late mailbox registration currently persists the new mailbox binding and republishes mailbox env vars into the owning tmux session, but long-lived interactive provider processes still rely on the launch-time process env snapshot. That split makes real unread detection and gateway wake-up prompts possible while leaving the live agent unable to use the new mailbox binding without relaunch.

The repository is converging on a stronger design assumption: managed agents live inside tmux-backed runtime containers, and tmux session environment is the mutable live control surface for that container. This change is needed now so late mailbox registration, mailbox skills, and gateway notifier behavior all use the same live binding authority instead of treating inherited process env as permanently authoritative.

## What Changes

- Add a runtime-owned live mailbox binding resolution contract for tmux-backed sessions that treats targeted tmux session env vars as the authoritative live mailbox projection for subsequent mailbox work.
- Keep the persisted session manifest as the durable mailbox capability record for resume, gateway adapter construction, and transport-safe secret-free state, while decoupling active mailbox work from stale launch-time process env.
- Update runtime-owned mailbox skills and mailbox prompts so agents resolve current mailbox bindings through the runtime-owned live binding path rather than assuming the provider process inherited current `AGENTSYS_MAILBOX_*` values at launch.
- Update gateway mail notifier readiness so notifier status and enablement depend on live mailbox actionability, not only on manifest mailbox presence.
- Remove the relaunch requirement for tmux-backed late mailbox registration flows when the runtime can refresh the live mailbox projection safely for subsequent mailbox work.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-mailbox-system-skills`: mailbox system skills and runtime-owned mailbox prompts use live tmux-backed mailbox binding resolution for active sessions instead of relying only on inherited process env.
- `agent-gateway-mail-notifier`: notifier readiness and enablement reflect live mailbox actionability for tmux-backed sessions after late mailbox mutation.
- `brain-launch-runtime`: tmux-backed sessions publish and refresh mailbox binding env in tmux session environment as the live mailbox projection for subsequent work while the manifest remains the durable record.

## Impact

- Affected code: `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/agents/realm_controller/gateway_service.py`, `src/houmao/agents/realm_controller/mail_commands.py`, `src/houmao/agents/mailbox_runtime_support.py`, tmux integration helpers, and projected mailbox skill assets.
- Affected docs/specs: mailbox runtime contracts, mailbox quickstart and internals, and gateway notifier contract docs.
- Affected tests: runtime mailbox mutation tests, tmux-backed late registration tests, gateway notifier readiness tests, and real-session integration coverage for late registration without relaunch.
