# Design

## Context

Kimi's native ACP entrypoint serves JSON-RPC on stdio. Its initialization advertises session and prompt capabilities. Loading a session can replay history, while the resume path binds a session without that replay. Some client capabilities redirect native filesystem or terminal operations through the client. [Kimi CLI entrypoint](../../../extern/orphan/kimi-code/apps/kimi-code/src/cli/sub/acp.ts), [ACP server](../../../extern/orphan/kimi-code/packages/acp-server/src/server.ts), and [history replay](../../../extern/orphan/kimi-code/packages/acp-server/src/replay.ts).

## Goals / Non-Goals

Provide `(kimi, service)` under the persistent owner from 04. Preserve the native Kimi home, role, execution context, user policy, and exact session. Optional ACP operations are exposed only when both the native build and the Houmao adapter implement their complete behavior.

## Decisions

### Share Transport Ownership and Negotiate Kimi's Dialect

Use the 04 service owner's bidirectional connection and continuous reader. Launch `kimi acp` with mode-specific launch policy. Record actual tool build, protocol revision, and negotiated capabilities. Keep the client-capability declaration minimal. Advertising client filesystem or terminal APIs changes where Kimi executes work and requires dedicated implementation and authorization. DSH's advertised operations and permission choices are an unsuitable default. [Kimi ACP startup](../../../extern/orphan/kimi-code/packages/acp-server/src/start.ts).

### Bind Session History Before Opening Admission

Create only when a new conversation is selected. On continuation use the saved Kimi native ID, private home, and workspace. Prefer qualified `session/resume` for direct continuation. If a qualified `session/load` path is used, mark its replay as history and fence it from current output and accounting. Accept only the confirmed session binding before opening admission. A failed resume returns an explicit outcome.

### Keep Reverse Requests and Cancellation Live

Process permission, supported interaction, and update messages while `session/prompt` is outstanding. Map native choices to `unattended` or `as_is` policy and handle unsupported questions promptly. Serialize session-scoped cancel with the active operation because the protocol target can outlive a single prompt. Classify late updates by their available provenance and keep uncorrelated ones out of the next request. [Permission bridge](../../../extern/orphan/kimi-code/packages/acp-server/src/approval.ts) and [interaction bridge](../../../extern/orphan/kimi-code/packages/acp-server/src/interaction-bridge.ts).

## Risks / Trade-offs

- Replayed output or a late update can be mistaken for a new response. Exercise resume/load, pending interaction and a second turn on the same session with separate event and usage assertions.
- A protocol feature may vary across installed Kimi builds. Check required methods at handshake and use explicit unsupported results for optional features.

## Migration Plan

Add the new capability to the support matrix after 04 is available and Kimi's own managed conformance passes. Qualify gateway detach, owner stop, explicit relaunch and exact continuation independently of the Kimi Web path. A failed qualification leaves `kimi_acp` unavailable for that build.
