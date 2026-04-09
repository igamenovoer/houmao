## Why

Direct managed-agent TUI interrupt is still gated by coarse tracked TUI state and can return a no-op when the visible session is already interruptible but the tracker has not caught up yet. That makes `houmao-mgr agents interrupt` unreliable for live TUI agents and forces callers to reason about Houmao's delayed state model instead of using one stable interrupt contract.

## What Changes

- Change transport-neutral managed-agent interrupt so TUI-backed agents always receive a best-effort `Escape` interrupt signal through the direct managed-agent path, even when coarse tracked state currently reports idle or unknown.
- Preserve current headless interrupt behavior, including active-work targeting and no-op semantics when no headless execution is active.
- Update the native `houmao-mgr agents interrupt` contract so server-backed TUI agents inherit the same best-effort `Escape` behavior as local interactive and gateway-backed TUI interrupts.
- Update packaged messaging guidance to document the transport split clearly: TUI interrupt means best-effort `Escape`, while headless interrupt means execution/process interruption.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-server-agent-api`: change `POST /houmao/agents/{agent_ref}/requests` so TUI interrupt uses best-effort `Escape` delivery instead of active-phase no-op gating.
- `houmao-srv-ctrl-native-cli`: document `houmao-mgr agents interrupt` as transport-neutral while making TUI interrupt delivery independent of delayed tracked active-state.
- `houmao-agent-messaging-skill`: document the user-facing interrupt contract split between TUI `Escape` delivery and headless execution interruption.

## Impact

- Affected code: managed-agent request submission in `src/houmao/server/service.py`, native CLI routing in `src/houmao/srv_ctrl/commands/managed_agents.py`, and packaged messaging skill docs under `src/houmao/agents/assets/system_skills/houmao-agent-messaging/`.
- Affected behavior: server-backed `houmao-mgr agents interrupt` and `POST /houmao/agents/{agent_ref}/requests` for TUI agents.
- Tests: managed-agent API contract tests, server request-submission tests, and CLI/request-path coverage for TUI interrupt behavior.
