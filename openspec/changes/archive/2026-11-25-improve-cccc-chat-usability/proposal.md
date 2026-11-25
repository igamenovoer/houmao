# Proposal

## Why

Two managed agents successfully exchanged threaded CCCC chat, retried a refused delivery, and reconnected without replay. The test exposed an ambiguous reply hint, an opaque CLI error, two undocumented driver assumptions, and stale compatibility guidance. [Issue #99](https://github.com/igamenovoer/houmao/issues/99)

## What Changes

- Give `houmao-cccc` callers actionable, redacted diagnostics for an invalid gateway URL and unavailable managed-self authority. Identify the gateway base URL separately from the plugin HTTP URL in chat hints, and show the CLI reply syntax using the advertised instance and scoped event reference.
- Document one prompt-readiness procedure for Web and headless drivers using the existing gateway status observation. Check CCCC binding health separately for a CCCC preflight.
- Specify the existing newest-first order for delivery receipt lookup, including which attempts the limit selects, in CLI help and the gateway and provider references.
- Correct the gateway SDK version and Houmao dependency range in the CCCC and plugin author references. Identify the CCCC external-receiver protocol version separately.

## Capabilities

### New Capabilities

### Modified Capabilities

- `cccc-chat` defines CLI endpoint diagnostic and reply guidance requirements and specifies the order of bounded delivery receipt reads.
- `agent-gateway-reference-docs` requires a discoverable Web and headless readiness procedure that uses existing gateway status.

## Impact

The change affects the optional `houmao-cccc` distribution, gateway references, agent examples, and focused CLI and provider tests. The gateway's existing endpoint and admission checks authorize each request. CCCC keeps the authoritative event and attempt records, and a new attempt requires an explicit sender decision.
