## 1. Managed-Agent State Contracts

- [x] 1.1 Add server API models for gateway summary, mailbox summary, managed-agent detailed state, and transport-neutral managed-agent request envelopes, reusing the shared coarse turn and diagnostics model families where applicable.
- [x] 1.2 Implement managed-agent summary-state projection so coarse `/houmao/agents/{agent_ref}/state` includes redacted gateway and mailbox posture for both TUI and headless agents.
- [x] 1.3 Implement `GET /houmao/agents/{agent_ref}/state/detail` with transport-discriminated TUI projection plus canonical-route pointer, headless detail that extends shared turn posture, and shared alias resolution.

## 2. Server-Owned Managed-Agent Control Surfaces

- [x] 2.1 Implement `POST /houmao/agents/{agent_ref}/requests` for `submit_prompt` and `interrupt`, including accepted-request envelopes, optional headless turn linkage, explicit `422`/`409`/`503` admission semantics, and explicit no-op interrupt handling when no active interruptible work exists.
- [x] 2.2 Implement managed-agent gateway routes for attach, detach, and status using server-owned service methods instead of runtime-private operator flows, including idempotent attach for already-attached healthy gateways and explicit conflict handling for stale or reconciliation-required attach state.
- [x] 2.3 Implement managed-agent gateway notifier routes that operate on the same underlying gateway notifier state as the direct gateway `/v1/mail-notifier` surface.

## 3. Gateway Execution Adapters And Runtime Integration

- [x] 3.1 Extract a typed gateway execution-adapter boundary from the current REST-backed gateway adapter implementation.
- [x] 3.2 Refactor `GatewayServiceRuntime` to select execution adapters from attach metadata while preserving existing REST-backed queueing, status, and admission behavior.
- [x] 3.3 Verify existing REST-backed gateway execution still behaves the same through the refactored adapter boundary.
- [x] 3.4 Implement the server-managed-agent gateway adapter so gateway request execution against server-managed agents flows through `houmao-server` APIs rather than local manifest bypasses.
- [x] 3.5 Implement the local-headless gateway adapter and extend runtime live gateway attach support for runtime-owned tmux-backed headless backends.

## 4. Headless Launch Mailbox Contract And Decoupled Gateway Lifecycle

- [x] 4.1 Revise the native headless launch request and server launch service so the official launch contract keeps structured mailbox overrides but does not accept launch-time gateway options.
- [x] 4.2 Keep gateway lifecycle attach or detach resolution separate from launch, with later attach flows using published tmux session env plus manifest-backed attach metadata and persisted gateway defaults instead of launch-coupled inputs.
- [x] 4.3 Keep server client coverage aligned with the new detailed-state, request-envelope, and managed-agent gateway routes without adding launch-coupled gateway behavior to `houmao-srv-ctrl`.

## 5. Verification And Follow-On Consumer Readiness

- [x] 5.1 Add unit coverage for managed-agent summary/detail state, shared turn and diagnostics reuse in headless detail, and request validation or admission semantics.
- [x] 5.2 Add integration coverage for server-managed gateway attach idempotence, notifier control projection, runtime-owned headless gateway attach behavior, and headless attach-metadata re-publication on resume.
- [x] 5.3 Update server and gateway documentation so managed-agent state, request submission, and gateway operations are documented as the official contract for later async mailbox demos, including the curated TUI projection split, the fact that gateway lifecycle remains post-launch, and the fact that `/v1/mail/*` proxying remains out of scope for this change.
