## 1. Managed-Agent State Contracts

- [ ] 1.1 Add server API models for gateway summary, mailbox summary, managed-agent detailed state, and transport-neutral managed-agent request envelopes, reusing the shared coarse turn and diagnostics model families where applicable.
- [ ] 1.2 Implement managed-agent summary-state projection so coarse `/houmao/agents/{agent_ref}/state` includes redacted gateway and mailbox posture for both TUI and headless agents.
- [ ] 1.3 Implement `GET /houmao/agents/{agent_ref}/state/detail` with transport-discriminated TUI projection plus canonical-route pointer, headless detail that extends shared turn posture, and shared alias resolution.

## 2. Server-Owned Managed-Agent Control Surfaces

- [ ] 2.1 Implement `POST /houmao/agents/{agent_ref}/requests` for `submit_prompt` and `interrupt`, including accepted-request envelopes, optional headless turn linkage, explicit `422`/`409`/`503` admission semantics, and explicit no-op interrupt handling when no active interruptible work exists.
- [ ] 2.2 Implement managed-agent gateway routes for attach, detach, and status using server-owned service methods instead of runtime-private operator flows, including idempotent attach for already-attached healthy gateways and explicit conflict handling for stale or reconciliation-required attach state.
- [ ] 2.3 Implement managed-agent gateway notifier routes that operate on the same underlying gateway notifier state as the direct gateway `/v1/mail-notifier` surface.

## 3. Gateway Execution Adapters And Runtime Integration

- [ ] 3.1 Extract a typed gateway execution-adapter boundary from the current REST-backed gateway adapter implementation.
- [ ] 3.2 Refactor `GatewayServiceRuntime` to select execution adapters from attach metadata while preserving existing REST-backed queueing, status, and admission behavior.
- [ ] 3.3 Verify existing REST-backed gateway execution still behaves the same through the refactored adapter boundary.
- [ ] 3.4 Implement the server-managed-agent gateway adapter so gateway request execution against server-managed agents flows through `houmao-server` APIs rather than local manifest bypasses.
- [ ] 3.5 Implement the local-headless gateway adapter and extend runtime live gateway attach support for runtime-owned tmux-backed headless backends.

## 4. Headless Launch And Shared Resolution

- [ ] 4.1 Extend the native headless launch request and server launch service to accept structured mailbox and gateway launch options.
- [ ] 4.2 Extract and reuse the existing runtime mailbox and gateway resolution helpers, including `resolve_effective_mailbox_config`, `bootstrap_resolved_mailbox`, and gateway listener or capability-publication resolution, so server-native headless launch follows the same effective configuration rules as runtime session startup.
- [ ] 4.3 Extend server client and `houmao-srv-ctrl` helpers to understand the new headless launch, detailed state, request-envelope, and gateway contracts.

## 5. Verification And Follow-On Consumer Readiness

- [ ] 5.1 Add unit coverage for managed-agent summary/detail state, shared turn and diagnostics reuse in headless detail, and request validation or admission semantics.
- [ ] 5.2 Add integration coverage for server-managed gateway attach idempotence, notifier control projection, runtime-owned headless gateway attach behavior, and headless attach-metadata re-publication on resume.
- [ ] 5.3 Update server and gateway documentation so managed-agent state, request submission, and gateway operations are documented as the official contract for later async mailbox demos, including the curated TUI projection split and the fact that `/v1/mail/*` proxying remains out of scope for this change.
