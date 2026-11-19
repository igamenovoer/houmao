# Design

## Context

The retained Houmao app-server client sends obsolete `turn/start` fields and closes its owned subprocess when the controller closes. Both runtime selection and backend creation reject it today. The local Codex app-server requires initialization and accepts typed v2 thread and turn messages. [Retired client](../../../src/houmao/agents/realm_controller/backends/codex_app_server.py), [native message processor](../../../extern/orphan/codex/codex-rs/app-server/src/message_processor.rs), and [protocol method table](../../../extern/orphan/codex/codex-rs/app-server-protocol/src/protocol/common.rs).

## Goals / Non-Goals

Use an explicitly owned per-agent stdio app-server under the service owner from 04. Qualify fresh launches, prompt/interrupt, approvals, observation, exact thread continuity, and operator lifecycle. External shared daemons and incompatible persisted handles are outside this adapter's ownership contract.

## Decisions

### Replace the Wire Client and Runtime Gate Together

Use the qualified native `codex app-server` stdio entrypoint with the selected `CODEX_HOME` and workspace. Send `initialize` with supported client identity/capabilities, await the response, and send `initialized`. Complete a real thread binding before publishing ready. Enabling the previously blocked backend name alone would leave the old request shape, initialization gap, and controller-lifetime process bug active.

### Track Managed Request, Thread, and Turn Independently

Use `thread/start` for explicit new work and `thread/resume` with the saved thread ID for continuation. Verify the returned thread and available workspace binding. Send `turn/start` with `threadId` and an `input` array of typed items. Associate `turn/started`, item notifications and `turn/completed` with the returned thread and turn IDs, including valid notifications that race the initial response. `turn/interrupt` carries both IDs. Preserve stop status, partial output, and missing data. [Native turn types](../../../extern/orphan/codex/codex-rs/app-server-protocol/src/protocol/v2/turn.rs).

### Service Server-Initiated Calls During Work

The shared owner drains messages continuously. Dispatch supported approval or input requests under the selected policy, reject unsupported methods promptly, and keep provider diagnostics separate. Deduplicate or bound duplicate notifications using attributable native evidence. The RPC acknowledgment confirms a request or turn handle. The native terminal notification provides the turn result.

### Constrain Activation and Recovery

Keep the selection gate for old manifests and incompatible protocols. Expose `(codex, service)` only for a current-schema owned launch that passes build and protocol checks. Ordinary manager exit or gateway detach releases the client connection to the owner. Explicit service stop closes the child. Reconcile a lost connection without resubmitting user input.

## Risks / Trade-offs

- A fake peer can accidentally repeat the legacy snake_case behavior. Compare fixtures with native types, then test a real pinned app-server running against an explicitly selected fixture configuration.
- Approval or completion can arrive out of order. Drive the reader through server-initiated calls, duplicate or foreign turn notifications, cancellation races, and a disconnect after admission.

## Migration Plan

Replace the block for newly qualified launches and update the tests that currently require every app-server launch to fail. Keep a failure case for obsolete authorities and missing capabilities. Advertise service independently of 05 after native conformance, with headless and TUI continuing to use their own adapters.
