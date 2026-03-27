## Context

Runtime-owned `local_interactive` sessions already sit inside the repo's tmux-backed runtime model. The runtime publishes gateway capability for them, the stable attach contract accepts `local_interactive`, gateway storage persists local attach metadata for them, and the gateway service already routes `local_interactive` attach contracts through the local runtime execution adapter.

The remaining mismatch is at the live attach boundary: `_attach_gateway_for_controller()` still rejects `local_interactive` even though the rest of the gateway model treats it as an attachable runtime-owned local session. The existing local runtime gateway path is also named and described as headless-first even though `LocalInteractiveSession` inherits the same local resumable base and already exposes the prompt and interrupt controls the gateway needs.

## Goals / Non-Goals

**Goals:**

- Allow live gateway attach for runtime-owned `local_interactive` sessions when the local runtime execution adapter exists.
- Make the local gateway execution path explicitly support both runtime-owned native headless sessions and runtime-owned `local_interactive` sessions.
- Preserve durable queueing, explicit unsupported-backend failures, and gateway-mediated prompt or interrupt semantics.
- Add regression coverage and docs for the newly supported local interactive flow.

**Non-Goals:**

- Redesign gateway storage, gateway HTTP routes, or runtime manifest formats.
- Introduce a new standalone gateway process model for local interactive sessions.
- Expand this change to full readiness-aware TUI tracking or new headless-control read routes for `local_interactive`.
- Change pair-managed `houmao_server_rest` gateway topology.
- Extract a broader cross-module supported-backend constant or otherwise widen this change into a general gateway-service modularization refactor.

## Decisions

### 1. Treat `local_interactive` as a supported runtime-owned local gateway target

The runtime attach gate will be aligned with the already-published gateway capability contract so that `local_interactive` is admitted when the local runtime gateway adapter is implemented.

This is the smallest design that removes the current boundary mismatch. Keeping `local_interactive` unsupported until a future redesign would continue publishing attachability metadata that the live attach path refuses to honor.

The implementation should also keep unsupported-backend failures truthful for the backends that remain unsupported after this change rather than leaving a stale hardcoded supported-backend list in operator-facing error text.

Alternative considered: leave the attach rejection in place until a dedicated interactive-only adapter exists. Rejected because the current runtime, schema, and gateway-storage layers already describe `local_interactive` as gateway-capable.

### 2. Use one local tmux-backed execution adapter for native headless and `local_interactive` runtimes

The gateway execution layer should treat runtime-owned local sessions as one adapter family backed by manifest resume plus tmux session identity, rather than splitting separate queueing or resume logic immediately.

`LocalInteractiveSession` already subclasses `HeadlessInteractiveSession` and already implements `send_prompt(...)` and `interrupt()`, so the gateway can reuse the same local runtime authority boundary. The implementation may rename the current `_LocalHeadlessGatewayAdapter` for clarity, but the key design decision is semantic broadening, not adapter proliferation.

Because the current implementation relies on `LocalInteractiveSession` satisfying the existing local resumable session boundary through that inheritance relationship, the implementation should make that invariant explicit in a local, readable way and should use backend-neutral operator wording for local tmux availability errors. A rename may help, but it remains optional.

Alternative considered: create separate local-headless and local-interactive adapter classes now. Rejected because it would duplicate resume, tmux liveness, and request-dispatch behavior without introducing a new durable contract.

### 3. Keep readiness and TUI tracking expansion out of this change

This change will make attach, status, prompt, and interrupt work through the gateway for `local_interactive`, but it will not require a new readiness-aware gateway policy or a new gateway-owned TUI-tracking contract for local interactive sessions.

The current local runtime gateway status posture can remain based on live tmux-backed reachability for this change. If later work needs stronger prompt-admission gating based on parsed TUI posture, that should be handled as a follow-up under the existing TUI tracking capabilities rather than bundled into this attach-enablement change.

Alternative considered: require gateway-owned TUI tracking and readiness inference before supporting local interactive attach. Rejected because it significantly broadens scope beyond the observed unsupported-backend failure and would delay a narrowly scoped correctness fix.

### 4. Validate behavior through runtime and gateway regression coverage

The change should be verified at both the runtime attach boundary and the gateway execution boundary. Tests should cover:

- attach succeeding for runtime-owned `local_interactive`,
- gateway status reporting a live attached gateway,
- gateway prompt dispatch reaching the live `local_interactive` runtime, and
- gateway interrupt dispatch using the gateway path rather than direct fallback.

Where tests need valid persisted `local_interactive` resume state, a dedicated local-interactive seed helper is preferred over overloading the existing headless-only helper with backend-conditional setup.

Alternative considered: rely only on existing headless gateway tests plus manual verification. Rejected because the current problem is a backend-specific mismatch that needs explicit regression coverage.

## Risks / Trade-offs

- [Risk] `local_interactive` prompt admission may still look open whenever the tmux session is live, even if the provider TUI is not truly ready. → Mitigation: keep failures explicit at prompt-delivery time, document the scope of this change, and defer readiness-aware gating to a follow-up capability.
- [Risk] Reusing a headless-origin adapter shape can leave naming or abstraction leaks in the code. → Mitigation: clarify adapter semantics in code and specs so the local adapter is understood as the shared runtime-owned local tmux-backed execution path.
- [Risk] Expanding the supported backend set could surface hidden assumptions in runtime recovery or gateway status handling. → Mitigation: add targeted unit and integration coverage for attach, status, prompt, and interrupt on `local_interactive`.

## Migration Plan

No schema migration is required. Existing attach contracts already accept `local_interactive`, so the implementation change is to honor that persisted contract during live attach and gateway execution.

Rollback remains straightforward: reverting the attach eligibility and adapter broadening returns the system to its previous unsupported state without requiring manifest or gateway-root cleanup.

## Open Questions

None for this change. Readiness-aware gateway admission and gateway-owned TUI tracking for runtime-owned `local_interactive` sessions are explicitly deferred.
