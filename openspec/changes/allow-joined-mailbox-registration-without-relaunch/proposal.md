## Why

Joined tmux sessions adopted through `houmao-mgr agents join` can already support manifest-backed control, gateway attach, and live tmux mailbox projection refresh, but late mailbox registration still rejects joined sessions whose relaunch posture is `unavailable`. That leaves the mailbox contract internally inconsistent: the runtime can safely mutate durable mailbox state and live tmux mailbox bindings for the joined session, yet the operator path still blocks registration because the session cannot be relaunched.

## What Changes

- Allow `houmao-mgr agents mailbox register` and `houmao-mgr agents mailbox unregister` to operate on joined tmux-backed sessions even when their joined relaunch posture is unavailable, as long as the runtime still has the managed authority needed to update durable mailbox state and the owning tmux session environment.
- Remove the special `unsupported_joined_session` activation posture for joined tmux sessions whose mailbox mutation becomes live immediately through tmux mailbox projection refresh.
- Make joined tmux sessions that successfully late-register a mailbox binding report `active` and become usable for runtime-owned `agents mail ...` flows and gateway mail-notifier flows without requiring relaunch solely for mailbox binding refresh.
- Keep non-relaunchable joined sessions non-relaunchable; this change does not invent restart authority or weaken the existing joined-session relaunch contract.
- Tighten the specs and docs so “supported tmux-backed managed sessions” explicitly includes Houmao-joined tmux sessions when mailbox mutation can be applied safely through manifest plus tmux live-binding updates.
- Require `houmao-mgr` to render expected operator-facing mailbox and gateway-notifier failures as clean CLI errors rather than leaking Python tracebacks from the top-level wrapper.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `managed-agent-mailbox-registration`: joined tmux sessions without relaunch posture no longer fail mailbox registration by default; supported joined tmux sessions become mailbox-active through live tmux binding refresh.
- `brain-launch-runtime`: runtime mailbox mutation semantics for tmux-backed sessions extend to joined tmux sessions whose relaunch posture is unavailable but whose live mailbox projection can still be updated safely.
- `agent-gateway-mail-notifier`: notifier support and enablement treat a joined tmux session with a successfully refreshed live mailbox projection as actionable, even if that session remains non-relaunchable.
- `houmao-srv-ctrl-native-cli`: expected mailbox-management and gateway-notifier command failures are rendered as explicit CLI errors without Python tracebacks.

## Impact

- Affected code: `src/houmao/agents/realm_controller/runtime.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, `src/houmao/srv_ctrl/commands/main.py`, gateway notifier readiness paths, and mailbox runtime helpers that publish tmux live mailbox projection.
- Affected tests: late mailbox registration runtime tests, managed-agent mailbox CLI tests, top-level CLI error-normalization tests, joined-session integration tests, and gateway notifier readiness tests for joined TUI sessions.
- Affected docs/specs: mailbox registration docs and specs that currently still describe or imply rejection for joined sessions without relaunch posture.
