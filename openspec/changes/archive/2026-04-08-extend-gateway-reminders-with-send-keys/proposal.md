## Why

The new `/v1/reminders` surface currently supports only semantic prompt delivery. That is not enough for workflows that need exact tmux-style control input such as `<[Escape]>`, slash-command submission, or other raw key sequences that must not be treated as literal prompt text.

We need to extend reminders now because the gateway already has a distinct raw `send-keys` control lane with different semantics, backend limits, and Enter behavior. Without a first-class reminder form for raw control input, callers must choose between lossy prompt reminders and ad hoc out-of-band automation.

## What Changes

- Extend gateway reminder delivery so one reminder may deliver either semantic `prompt` text or raw `send_keys` control input.
- Add `send_keys.sequence` as a reminder delivery payload for exact `<[key-name]>` control-input behavior.
- Add `send_keys.ensure_enter` with default `true`, meaning send-keys reminders ensure one trailing Enter instead of forcing callers to append `<[Enter]>` every time.
- Remove any reminder-specific `escape_special_keys` concept; send-keys reminders are explicitly for exact special-key semantics rather than literal whole-string escaping.
- Define that `title` remains required for reminder inspection, but send-keys reminders do not submit `title` or `prompt` text when they fire.
- Require exactly one delivery form per reminder: either `prompt` or `send_keys`.
- Validate send-keys reminder support against the current gateway backend boundary and fail explicitly on create or update when the attached target cannot preserve raw control-input semantics.
- Update gateway skill guidance and gateway reference docs to describe send-keys reminders, `ensure_enter`, and the direct live HTTP boundary clearly.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: reminder requirements change from prompt-only delivery to a tagged delivery model that supports either semantic `prompt` delivery or raw `send_keys` delivery with `ensure_enter`.
- `houmao-agent-gateway-skill`: gateway skill guidance changes to explain send-keys reminders, their exact-key boundary, and the lack of any new `houmao-mgr agents gateway reminders ...` CLI family.
- `agent-gateway-reference-docs`: gateway reference docs change to explain send-keys reminder behavior, backend limits, and `ensure_enter` semantics accurately.

## Impact

- Affected code: `src/houmao/agents/realm_controller/gateway_models.py`, `src/houmao/agents/realm_controller/gateway_service.py`, `src/houmao/agents/realm_controller/gateway_client.py`, reminder tests, and the packaged `houmao-agent-gateway` system skill assets.
- Affected API: `/v1/reminders` request and inspection models expand to support `send_keys` delivery and `ensure_enter`; existing prompt reminders remain supported.
- Affected docs: gateway reminder reference docs and packaged gateway skill reminder guidance need to explain exact raw-control reminder behavior and backend rejection cases honestly.
