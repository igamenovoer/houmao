## Why

`houmao-mgr agents list` and `houmao-mgr agents gateway status` can return populated structured payloads while printing `No managed agents.` or `(no gateway status)` in human-oriented output modes. This misleads operators and user-controlled agents because the CLI presentation layer drops valid Pydantic model payloads before curated plain/fancy renderers can interpret them.

The existing print-style spec already requires `BaseModel` normalization before rendering in all modes, so this change is needed now to bring the custom-renderer path back into compliance and to restore trustworthy CLI output for managed-agent inspection commands.

## What Changes

- Normalize structured payloads before dispatching curated plain and fancy renderers so Pydantic `BaseModel` responses render correctly in all print styles.
- Tighten the print-style contract to cover curated renderer paths explicitly, not just the generic fallback path.
- Add regression coverage for managed-agent inspection commands whose human-oriented output currently becomes empty despite valid registry and gateway state.

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `houmao-mgr-print-style`: Require `emit()` to normalize Pydantic model payloads before invoking curated plain/fancy renderers so structured commands render consistently in `plain`, `json`, and `fancy` modes.

## Impact

- Output dispatch and renderer integration in `src/houmao/srv_ctrl/commands/output.py`.
- Managed-agent and gateway curated renderers in `src/houmao/srv_ctrl/commands/renderers/`.
- Regression coverage for `houmao-mgr agents list` and `houmao-mgr agents gateway status`.
