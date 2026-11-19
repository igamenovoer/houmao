# Design

## Context

The DSH protocol adapter initializes a process, runs one turn, applies optional session-scoped settings, and closes it. Closing the connection used to clear those settings. The current refresh assessment also assumes that a later turn reads newly materialized inputs. A persistent process changes both boundaries. [ACP driver](../../../src/houmao/agents/realm_controller/backends/dsh_acp_driver.py) and [native refresh](../../../src/houmao/agents/realm_controller/native_refresh.py).

## Goals / Non-Goals

Own exactly one native control connection per managed service incarnation. Independent manager commands, gateway processes, and passive readers can use the same live agent. Implement DSH ACP first and leave the service owner's state machine reusable for Kimi ACP and Codex app-server.

## Decisions

### Use a Per-Agent Owner in the Saved Execution Context

Start a Houmao service owner inside the managed tmux envelope. It launches the child, owns both stdio directions, drains stderr, and exposes a private local request channel in the agent's protected runtime directory. Bind client attachment to the current manifest, owner generation and execution locator. The gateway uses its existing per-agent authentication. Remote clients reach the owner through their saved executor or authenticated gateway. A transient controller holding stdin would lose the connection on every command exit.

### Track Service and Turn Identities Separately

Persist managed generation, provider incarnation, native logical session, and active managed request with protocol-specific correlation. Hold a single mutation slot and durably record intent before native input. Recheck identity and revocation at handoff. Keep reading native replies, reverse requests, and notifications during prompts and cancellation. Distinguish initializing, ready, busy, unavailable and uncertain work in observation. Gateway restart and read-only inspection reconnect to the owner. If the owner or its pipes die, reconcile evidence and permit a new incarnation only through the authorized lifecycle path. Orphan cleanup must verify process identity before signalling.

### Give DSH Explicit ACP Semantics

Launch `dsh --profile acp` with its managed configuration, initialize, negotiate, then `session/new` or `session/resume` the exact session. Keep the connection open between prompts. Use session updates and correlated prompt settlement for output, the existing native handoff fence for immediate dispatch, and the native journal for accounting. Route supported permission requests under the selected policy and fence session-scoped `session/cancel` against a newer managed request. Close the session and reap the owned process when the service stops. [DSH native ACP implementation](../../../extern/orphan/deepseek-harness/packages/acp/acp/src/index.ts).

### Treat Persistent Settings as Shared State

For a request model or reasoning override implemented by `session/set_config_option`, capture the effective prior value, serialize apply/prompt/restore, and verify restoration on all exit paths. If the build cannot do this safely, reject that option before mutation. An uncertain restore blocks conflicting work. Qualify resource reads at process creation, session binding, or native live refresh. Test role, MCP, skills, home edits, and journal offsets independently. A new prompt on an existing session is insufficient evidence of a configuration reload.

## Risks / Trade-offs

- Lost responses can release a slot twice or cause duplicate input. Test crashes before handoff, after native admission and before receipt persistence, late notifications, and reattachment through a new gateway process.
- Readiness can outlive a dead child in tmux. Verify the child connection and exact session, fence stale sockets, and expose the supervisor only as owner-side diagnostics.

## Migration Plan

Land the service owner behind the 02 contract, then register `dsh_acp` exclusively for qualified service launches. Exercise lifecycle takeover and cold resume with a fresh current-schema authority. The DSH release waits for both the one-shot and persistent paths. Later changes 05 and 06 reuse this owner, and neither is a prerequisite for the DSH cutover.
