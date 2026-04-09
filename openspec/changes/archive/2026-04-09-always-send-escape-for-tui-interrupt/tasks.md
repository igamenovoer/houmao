## 1. Direct TUI Interrupt Behavior

- [x] 1.1 Update the direct managed-agent request path in `src/houmao/server/service.py` so TUI-backed `interrupt` requests dispatch best-effort `Escape` instead of no-op gating on coarse tracked TUI phase.
- [x] 1.2 Preserve the existing headless interrupt admission and explicit no-op behavior when no headless execution is active.
- [x] 1.3 Adjust transport-neutral interrupt response detail where needed so TUI acceptance means interrupt signal dispatch rather than confirmed active-turn cancellation.

## 2. CLI And Messaging Guidance

- [x] 2.1 Verify the server-backed `houmao-mgr agents interrupt` path inherits the updated TUI interrupt contract without requiring raw `send-keys`.
- [x] 2.2 Update the packaged `houmao-agent-messaging` skill docs to explain that TUI interrupt means best-effort `Escape` while headless interrupt targets active execution.

## 3. Verification

- [x] 3.1 Add or update focused tests for direct managed-agent TUI interrupt acceptance when tracked TUI state is non-active but the TUI control path is reachable.
- [x] 3.2 Add or update focused tests that headless interrupt still returns explicit no-op behavior when no headless work is active.
- [x] 3.3 Run the relevant unit test slices for managed-agent request submission, native CLI interrupt routing, and messaging-skill/documentation coverage.
