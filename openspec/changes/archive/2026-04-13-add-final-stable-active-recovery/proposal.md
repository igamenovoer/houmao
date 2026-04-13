## Why

Gateway prompt control can remain blocked when a TUI detector misjudges a stable prompt-ready surface as `active`; the existing 5-second stale-active recovery is intentionally narrow and does not cover all detector false positives. We need a final, slower recovery guard that treats a stable unchanged TUI surface plus independent prompt-ready evidence as enough to clear the active posture.

## What Changes

- Add a final stable-active recovery tier for live TUI tracking with a default window of 20 seconds.
- Recover `turn.phase=active` to `ready` when the raw visible surface and published tracked state remain unchanged for the configured window and independent readiness evidence says the prompt is safe to use.
- Allow this final recovery to correct `surface.ready_posture=no` when the stronger evidence shows `parsed_surface.business_state=idle`, `parsed_surface.input_mode=freeform`, `surface.accepting_input=yes`, and `surface.editing_input=no`.
- Keep normal completion settlement as the only path that manufactures `last_turn.result=success`; final recovery is a readiness correction, not a success verdict.
- Make active turn anchors expire as stale when final recovery fires so gateway prompting is not blocked by an old anchor after the fallback has deliberately reopened input.
- Expose the new final recovery timing through existing gateway TUI timing configuration surfaces, with default 20 seconds and positive-value validation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `official-tui-state-tracking`: add the final stable-active recovery semantics to the live tracked-state contract.
- `agent-gateway`: include final stable-active recovery seconds in gateway-owned TUI tracking timing configuration and metadata.
- `houmao-server-agent-api`: allow managed-agent gateway attach requests to carry the new timing field with the existing gateway TUI timing overrides.
- `houmao-mgr-project-easy-cli`: expose the new gateway TUI timing override for launch-time gateway auto-attach.

## Impact

- Affected code: `src/houmao/server/tui/tracking.py`, `src/houmao/server/models.py`, `src/houmao/shared_tui_tracking/session.py` if raw surface signature plumbing is needed, and gateway timing config/model/CLI forwarding under `src/houmao/agents/realm_controller/` and `src/houmao/srv_ctrl/commands/`.
- Affected tests: live TUI tracker recovery tests, gateway timing config tests, server attach contract tests, and CLI timing option tests.
- Affected docs/specs: gateway TUI timing references and live tracked-state documentation should describe the new 20-second final recovery window.
- No public tracked-state shape change is required beyond adding the new timing metadata/config field.
