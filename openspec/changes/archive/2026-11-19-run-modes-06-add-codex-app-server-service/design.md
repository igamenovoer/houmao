# Design

## Context

The retired client used obsolete `turn/start` fields and tied process lifetime to a controller. The local Codex source at `0910087` requires initialization and uses typed v2 thread and turn messages. The selected installed build is `0.169.0`. Verify its actual behavior separately. The shared owner and prewrite guard from 04 and 05 already serve both ACP providers. [Native message processor](../../../extern/orphan/codex/codex-rs/app-server/src/message_processor.rs), [protocol method table](../../../extern/orphan/codex/codex-rs/app-server-protocol/src/protocol/common.rs).

## Goals / Non-Goals

Use an explicitly owned per-agent stdio app-server under the service owner from 04. Qualify fresh launches, prompt/interrupt, approvals, observation, exact thread continuity, and operator lifecycle. External shared daemons and incompatible persisted handles are outside this adapter's ownership contract.

## Decisions

### Replace the Wire Client and Runtime Gate Together

Use `codex app-server --listen stdio://` over the shared supervisor's bounded child connection. The transport applies Codex's unversioned wire envelope independently of ACP. Resolve and version-check the executable before startup. Verify the returned `codexHome`, send `initialized`, and bind a verified thread before reporting readiness. Role instructions and operator policy use typed native parameters or the managed home. Raw listener, daemon, and proxy arguments are outside the launch contract.

### Track Managed Request, Thread, and Turn Independently

Use a durable `thread/start` for a new conversation. Verify private-home thread metadata and the saved workspace before exact `thread/resume`. Avoid cwd, history and path overrides and exclude replayed turns from the resume response. Send `turn/start` with `threadId` and typed text input only when the bound thread and managed owner are idle. Native `turn/start` can steer an existing turn. Recheck the request permission under the write lock. Buffer earlier notifications within a fixed bound and use only those matching the thread and returned turn. `turn/interrupt` carries both IDs and waits for an attributable native terminal. [Native thread types](../../../extern/orphan/codex/codex-rs/app-server-protocol/src/protocol/v2/thread.rs), [native turn types](../../../extern/orphan/codex/codex-rs/app-server-protocol/src/protocol/v2/turn.rs).

### Service Server-Initiated Calls During Work

The owner drains messages continuously. Apply the selected native approval policy and decline residual requests that require human action. Validate the live thread and turn before answering supported reverse methods. Return bounded errors for undeclared methods and keep native diagnostics private. Use stable item identities and terminal status to fence late or duplicate notifications. Accounting requires an attributable native turn and source. Thread-wide totals or context size alone cannot establish a request charge.

### Constrain Activation and Recovery

Retained app-server manifests with the retired state shape cannot supply a current service identity. Attach verifies the saved incarnation, generation, native thread and private channel. Ordinary manager exit or gateway detach leaves the child under its owner. Explicit service stop closes the child. Transport loss after write preserves the original request and any verified handle, reports uncertainty, and avoids resending.

## Risks / Trade-offs

- A fake peer can accidentally repeat the legacy snake_case behavior. Compare fixtures with native types, then test a real pinned app-server running against an explicitly selected fixture configuration.
- Approval or completion can arrive out of order. Drive the reader through server-initiated calls, duplicate or foreign turn notifications, cancellation races, and a disconnect after admission.

## Migration Plan

Replace the block for newly qualified launches and retain failure cases for obsolete authorities. Verify the native app-server with the explicitly selected self-hosted `Qwen/Qwen3.8-27B-FP8` Responses route. A direct request to the local `/v1/responses` endpoint completed during review. Test Codex headless and TUI separately with the same model.
