# Design

## Context

Change 03 binds DSH headless to `dsh_headless` and leaves `dsh_acp` unqualified for new launches. The former per-turn ACP driver has concurrent protocol reading and permission handling that the persistent adapter can reuse. Closing its connection used to clear temporary settings. The qualified headless skill refresh refers to a later CLI invocation. Neither boundary applies to an already-open ACP session. [ACP driver](../../../src/houmao/agents/realm_controller/backends/dsh_acp_driver.py) and [native refresh](../../../src/houmao/agents/realm_controller/native_refresh.py).

## Goals / Non-Goals

Own exactly one native control connection per managed service incarnation. Independent manager commands, gateway processes, and passive readers can use the same live agent. Implement DSH ACP first and leave the service owner's state machine reusable for Kimi ACP and Codex app-server.

## Decisions

### Use a Per-Agent Owner in the Saved Execution Context

Start a Houmao service owner inside the managed tmux envelope. It launches the child, owns both stdio directions, drains stderr, and exposes a Unix request socket in a private owner directory. Store its exact address and process birth identity in a private runtime descriptor. A short socket directory accommodates long runtime paths. Bind attachment to the current manifest, owner generation, service incarnation, and execution locator. Register the managed identity without a human surface. The gateway keeps its existing per-agent authentication, and remote manager requests follow the saved executor.

### Track Service and Turn Identities Separately

Reuse change 02's full manifest-and-generation owner reservation and request identity. The private owner validates that claim before input, then updates the request's durable evidence with its service incarnation, native session, and available wire correlation. Use a bounded completion or uncertainty record even if the calling manager or gateway has exited. Keep reading replies, reverse requests, and notifications during prompts and cancellation. Project readiness through `ManagedControlObservationV1`, with distinct owner, connection, and operation evidence. Gateway and passive readers reconnect to the same owner. Loss of the owner or its pipes requires explicit recovery. Reuse the verified process and descendant cleanup principles from change 03.

### Give DSH Explicit ACP Semantics

Launch `dsh --profile acp` with its managed configuration, initialize, negotiate, then `session/new` or `session/resume` the exact session. Keep the connection open between prompts. Use session updates and correlated prompt settlement for output, the existing native handoff fence for immediate dispatch, and the native journal for accounting. Route supported permission requests under the selected policy and fence session-scoped `session/cancel` against a newer managed request. Close the session and reap the owned process when the service stops. [DSH native ACP implementation](../../../extern/orphan/deepseek-harness/packages/acp/acp/src/index.ts).

### Treat Persistent Settings as Shared State

For a request model or reasoning override implemented by `session/set_config_option`, capture the effective prior value, serialize apply/prompt/restore, and verify restoration on all exit paths. If the build cannot do this safely, reject that option before mutation. An uncertain restore blocks conflicting work. Qualify resource reads at process creation, session binding, or native live refresh. Test role, MCP, skills, home edits, and journal offsets independently. A new prompt on an existing session is insufficient evidence of a configuration reload.

## Risks / Trade-offs

- Lost responses can release a slot twice or cause duplicate input. Test crashes before handoff, after native admission and before receipt persistence, late notifications, and reattachment through a new gateway process.
- Readiness can outlive a dead child in tmux. Verify the child connection and exact session, fence stale sockets, and expose the supervisor only as owner-side diagnostics.

## Migration Plan

Land the service owner behind the 02 contract, then register `dsh_acp` exclusively for qualified service launches. Exercise lifecycle takeover and exact cold resume with the current manifest and registry schemas. Use DSH `0.2.2-rc.3` and the self-hosted `Qwen/Qwen3.8-27B-FP8` fixture inputs already qualified in changes 02 and 03. Record each run under `logs/` and use its recorded private tmux socket. The DSH release waits for the one-shot and persistent paths. Later changes 05 and 06 reuse this owner.
