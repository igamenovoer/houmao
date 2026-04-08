# Enhancement: Enable Gateway-Owned TUI State Tracking For `local_interactive` Sessions

> Obsolete as of 2026-04-08.
> Moved from `context/issues/enhance/enhance-gateway-tui-state-tracking-for-local-interactive-sessions.md` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Priority
P2 - Gateway attach and request delivery already work for serverless `local_interactive` sessions, but the gateway still does not expose its TUI tracking surface for that backend. This is not a core runtime failure, but it leaves a visible capability gap in the local interactive control plane.

## Status
Open as of 2026-03-25.

## Summary

The agent gateway already contains TUI state tracking functionality, but in the current implementation that functionality is only activated for attach contracts whose backend is `cao_rest` or `houmao_server_rest`.

As a result, a live attached gateway for a serverless `local_interactive` session can currently:

- accept prompt requests
- accept interrupt requests
- report general gateway health/status

but it cannot currently provide gateway-owned:

- current TUI state
- TUI history
- explicit prompt-submission tracking evidence

for that same local interactive session.

This looks like an implementation gap, not a fundamental architectural restriction.

## Reproduction

### 1. Launch a no-server local interactive TUI session

```bash
AGENTSYS_AGENT_DEF_DIR=/data1/huangzhe/code/houmao/tests/fixtures/agents \
pixi run houmao-mgr agents launch \
  --agents gpu-kernel-coder \
  --provider claude_code \
  --session-name verify-gateway-local-tracking \
  --yolo
```

### 2. Attach a gateway

```bash
pixi run houmao-mgr agents gateway attach 108187a69069c63bb6df84b9eea21a90
```

Observed result:

- gateway attach succeeds
- gateway prompt/interrupt path is usable

### 3. Attempt to use gateway-owned TUI tracking routes

The gateway service currently raises:

```text
Gateway TUI live-state routes are only available for attached TUI backends.
```

because `m_tui_tracking` was never started for the `local_interactive` attach contract.

## Current Implementation Shape

The gateway runtime already has a TUI tracking subsystem:

- `GatewayServiceRuntime.start()` calls `_start_tui_tracking_locked()`
- `GatewayServiceRuntime.get_tui_state()`
- `GatewayServiceRuntime.get_tui_history()`
- `GatewayServiceRuntime.note_tui_prompt_submission()`

These live in:

- `src/houmao/agents/realm_controller/gateway_service.py`

The gateway-owned tracker is backed by:

- `SingleSessionTrackingRuntime`

from:

- `src/houmao/shared_tui_tracking/ownership.py`

The immediate blocker is in:

- `src/houmao/agents/realm_controller/gateway_service.py`

`_tui_tracking_identity_locked()` currently returns `None` unless:

- `attach_contract.backend == "cao_rest"`, or
- `attach_contract.backend == "houmao_server_rest"`

That prevents the gateway from starting `m_tui_tracking` for `local_interactive`.

## Why This Looks Like A Small Feature Gap

### 1. The gateway already supports local interactive request execution

`_build_gateway_execution_adapter()` already routes `local_interactive` to the local tmux-backed adapter:

- `src/houmao/agents/realm_controller/gateway_service.py`

That means the gateway already recognizes `local_interactive` as a supported execution target.

### 2. The tracker identity model does not fundamentally require CAO metadata

`HoumaoTrackedSessionIdentity` supports:

- `tracked_session_id`
- `session_name`
- `tool`
- `tmux_session_name`
- optional `tmux_window_name`
- optional `terminal_aliases`
- optional agent metadata
- optional manifest/session-root metadata

in:

- `src/houmao/server/models.py`

Nothing in that model requires a CAO terminal id.

### 3. The tracking layer already tolerates missing terminal aliases

`_terminal_alias(identity)` falls back to `tracked_session_id` when `terminal_aliases` is empty:

- `src/houmao/server/tui/tracking.py`

So a `local_interactive` tracked identity does not need a CAO-style terminal alias to function.

### 4. `local_interactive` already publishes enough data for a tracked identity

The gateway attach contract already provides:

- backend kind
- `tmux_session_name`
- `manifest_path`
- `agent_def_dir`
- `runtime_session_id`
- attach identity

and the manifest can supply:

- tool
- observed tool version
- agent name
- agent id

That appears sufficient to construct a valid `HoumaoTrackedSessionIdentity`.

## Likely Implementation Direction

### 1. Allow `local_interactive` to build a tracking identity

Extend `_tui_tracking_identity_locked()` so it can construct a `HoumaoTrackedSessionIdentity` for `local_interactive`.

Likely mapping:

- `tracked_session_id`: `runtime_session_id` or `attach_identity`
- `session_name`: same value
- `tool`: from manifest
- `observed_tool_version`: from manifest launch-policy provenance when available
- `tmux_session_name`: from attach contract
- `tmux_window_name`: `None` unless later published
- `terminal_aliases`: empty list or a stable synthetic alias
- `agent_name`: from manifest
- `agent_id`: from manifest
- `manifest_path`: from attach contract
- `session_root`: from gateway paths/session root

### 2. Start the same tracking runtime for `local_interactive`

Once identity construction works, `GatewayServiceRuntime.start()` should automatically create and start `SingleSessionTrackingRuntime` for attached `local_interactive` sessions just as it already does for the supported REST-backed TUI cases.

### 3. Keep this scoped to gateway-local capability

This enhancement should not require any change to `houmao-server` admission, discovery, or projection behavior.

The target here is only:

- the gateway process itself
- for a locally attached `local_interactive` session
- exposing accurate gateway-owned TUI tracking state/history

## Design Notes

This is intentionally separate from broader distributed-agent or server-discovery work.

The enhancement does not require:

- CAO compatibility
- `houmao_server_rest`
- server-owned registration
- shared-registry-based `houmao-server` session admission

It is a local gateway/runtime capability improvement.

## Acceptance Criteria

- A live attached gateway for a `local_interactive` session starts `SingleSessionTrackingRuntime`.
- Gateway-local TUI state routes succeed for `local_interactive` instead of returning a 422 unsupported-backend response.
- Gateway-local TUI history routes succeed for `local_interactive`.
- Explicit prompt submission through the gateway updates gateway-owned TUI tracking state for `local_interactive`.
- Automated coverage verifies gateway-owned TUI tracking behavior for a local interactive session without involving `houmao-server`.
