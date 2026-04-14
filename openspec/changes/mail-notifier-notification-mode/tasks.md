## 1. Gateway Notifier Models And Storage

- [ ] 1.1 Add a notifier mode enum or literal type covering `any_inbox` and `unread_only` in gateway notifier models.
- [ ] 1.2 Add `mode` to `GatewayMailNotifierPutV1` with default `any_inbox` and strict validation for supported values.
- [ ] 1.3 Add `mode` to `GatewayMailNotifierStatusV1` and ensure disabled statuses still report the effective mode.
- [ ] 1.4 Persist notifier mode in gateway notifier storage and default missing stored mode to `any_inbox` without adding broader migration compatibility.

## 2. Gateway Notifier Runtime

- [ ] 2.1 Update notifier enablement to store the requested mode and include mode in notifier logs/status where useful.
- [ ] 2.2 Update notifier polling so mode `any_inbox` uses inbox `read_state=any`, `answered_state=any`, `archived=false`.
- [ ] 2.3 Update notifier polling so mode `unread_only` uses inbox `read_state=unread`, `answered_state=any`, `archived=false`.
- [ ] 2.4 Preserve existing readiness, prompt-readiness, busy-skip, poll-error, and repeat-notification behavior in both modes.
- [ ] 2.5 Update notifier prompt rendering so prompts name the effective mode and keep archive as completion instead of read or mark-read.

## 3. CLI And Proxy Surfaces

- [ ] 3.1 Add `--mode any_inbox|unread_only` to `houmao-mgr agents gateway mail-notifier enable`, defaulting to `any_inbox`.
- [ ] 3.2 Thread mode through native CLI helper functions and pair-authority dispatch without dropping it.
- [ ] 3.3 Ensure direct gateway clients, server clients, passive-server clients, and proxy handlers preserve `mode` through `GatewayMailNotifierPutV1` and `GatewayMailNotifierStatusV1`.
- [ ] 3.4 Update CLI and proxy tests for omitted-mode defaulting, explicit `unread_only`, invalid mode rejection, and status payload preservation.

## 4. Skills And Documentation

- [ ] 4.1 Update `houmao-process-emails-via-gateway` guidance to honor prompt-provided `any_inbox` or `unread_only` mode while preserving archive-after-processing.
- [ ] 4.2 Update `houmao-agent-gateway` mail-notifier guidance to describe `any_inbox` default, `unread_only` opt-in behavior, and the read-but-unarchived trade-off.
- [ ] 4.3 Update gateway mail-notifier prompt template text to remove stale unread-as-completion and mark-read completion wording.
- [ ] 4.4 Update `docs/reference/gateway/operations/mail-notifier.md` with mode behavior, status field coverage, prompt wording, and archive completion.
- [ ] 4.5 Update `docs/reference/cli/agents-gateway.md` with the notifier mode option, allowed values, and default.

## 5. Verification

- [ ] 5.1 Add or update gateway runtime tests proving `any_inbox` notifies for read or answered unarchived inbox mail and skips archived mail.
- [ ] 5.2 Add or update gateway runtime tests proving `unread_only` notifies unread unarchived inbox mail but skips read unarchived inbox mail.
- [ ] 5.3 Add or update prompt-rendering tests for mode-aware wording and absence of mark-read-as-completion wording.
- [ ] 5.4 Run focused unit tests for gateway notifier runtime, client/proxy contracts, CLI command wiring, and system skill docs.
- [ ] 5.5 Run `pixi run ruff check src tests`, `pixi run typecheck`, and the relevant pytest suites before marking the change complete.
