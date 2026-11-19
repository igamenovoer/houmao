# Design

## Context

Kimi's ACP entrypoint serves JSON-RPC on stdio. Initialization advertises session and prompt capabilities. Loading a session replays history, while resume binds a session directly. Client capability flags can redirect native filesystem or terminal operations through the client. The local reference is `67325c1`, and the selected executable is `2.6.0`. Check the installed wire behavior during qualification. [Kimi CLI entrypoint](../../../extern/orphan/kimi-code/apps/kimi-code/src/cli/sub/acp.ts), [ACP server](../../../extern/orphan/kimi-code/packages/acp-server/src/server.ts), [history replay](../../../extern/orphan/kimi-code/packages/acp-server/src/replay.ts).

## Goals / Non-Goals

Provide `(kimi, service)` under the persistent owner from 04. Preserve the native Kimi home, role, execution context, user policy, and exact session. Optional ACP operations are exposed only when both the native build and the Houmao adapter implement their complete behavior.

## Decisions

### Share Transport Ownership and Negotiate Kimi's Dialect

Reuse `ManagedServiceSession` and the 04 supervisor. Reuse the bounded JSON-RPC reader and process ownership from DSH with Kimi-specific initialization and permission handlers. Use `kimi acp` with mode-specific policy, native `SYSTEM.md`, and model and credentials projected into the private Kimi home. Keep client capabilities empty until the owner implements and authorizes a facility. That keeps filesystem and terminal work within the native execution context. [Kimi ACP startup](../../../extern/orphan/kimi-code/packages/acp-server/src/start.ts).

### Bind Session History Before Opening Admission

Create only when a new conversation is selected. Use the exact native ID and check its durable location in the selected private home and workspace before calling `session/resume` or a negotiated `session/load` fallback. Kimi restores by ID and the reply omits the ID. A `cwd` parameter or list response alone does not prove the workspace. Drain binding-time history before opening admission. The first request snapshots the current journal position, so past usage and replay stay outside its interval. A failed bind returns an explicit outcome.

### Separate Transport Handoff From Native Settlement

Reuse the current owner reservation, request ID, and immediate prewrite authorization. Persist the write attempt before stdio input. The wire write certifies handoff to the owned transport. A correlated prompt reply and exact post-baseline native main-turn journal certify ordinary turn settlement. A bare `end_turn` can also represent a local slash command or a hook-blocked launch. The ordinary prompt path refuses native slash commands before writing. Missing or contradictory terminal evidence yields a truthful failure or uncertainty and no replay. Session-scoped ACP display and context-occupancy updates cannot settle a request or generate usage. The native per-turn usage records provide the accounting source.

### Keep Reverse Requests and Cancellation Live

Process reverse requests while `session/prompt` is outstanding. Let native `unattended` or `as_is` policy make its configured decisions and decline pending approvals, questions, and plan reviews that require human input. Serialize session-scoped cancellation with the exact live operation because the native target can outlive a prompt. Sending the notification alone conveys a cancellation attempt. A correlated response and available terminal journal evidence report the outcome. [Permission bridge](../../../extern/orphan/kimi-code/packages/acp-server/src/approval.ts), [interaction bridge](../../../extern/orphan/kimi-code/packages/acp-server/src/interaction-bridge.ts).

## Risks / Trade-offs

- Replayed output or a late update can be mistaken for a new response. Exercise resume/load, pending interaction and a second turn on the same session with separate event and usage assertions.
- A protocol feature may vary across installed Kimi builds. Check required methods at handshake and use explicit unsupported results for optional features.

## Migration Plan

Qualify the manager, authenticated gateway, passive and AG-UI projections with the same exact owner identity. Use self-hosted `Qwen/Qwen3.8-27B-FP8` and the explicitly selected Kimi binary. Compare behavior against Kimi headless and TUI. A failed native qualification leaves `kimi_acp` unavailable for that build.
