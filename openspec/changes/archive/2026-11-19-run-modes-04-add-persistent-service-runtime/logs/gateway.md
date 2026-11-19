# Gateway and AG-UI Verification

The gateway dispatches `service` requests through the verified `dsh_acp` owner. A direct or AG-UI receipt records the reserved Houmao request ID. The service owner records handoff after the native protocol accepts the prompt, and its durable record ties the outcome to the service incarnation, native conversation, and native turn. The signed service state and request routes return that evidence after a gateway restart. The public attach record omits a human surface for this mode.

Ordinary plugin delivery requires the shared owner slot and honors permission revocation before native input. A busy plugin call returns HTTP 409 and records `not_sent` without creating delayed work. The periodic filesystem mailbox notifier uses the same owner slot for its queued wake. Service interrupts carry the exact captured request ID to the owner and the native provider.

## Controlled DSH rc.3 Integration

`tests/integration/agents/dsh/test_service_gateway.py::test_gateway_reconnects_to_exact_active_service_request` held a native prompt open, checked that a competing signed gateway prompt received HTTP 409, detached and reattached the gateway, and retrieved the original request while active and after completion. The external `GatewayClient` decoded the canonical event JSON, and the usage ledger retained the exact managed request. A signed AG-UI SSE run on the same owner returned the exact native assistant text and `RUN_FINISHED`.

`tests/integration/agents/dsh/test_service_gateway.py::test_service_plugin_and_periodic_mail_use_the_same_owner_slot` rejected plugin delivery while a competing claim held the slot. The provider observed no prompt and the queue stayed empty. The test then handed one plugin wake and two periodic mail wakes to the same persistent owner and native conversation. Both integration cases passed in 22.58 seconds.

## Fault and Projection Coverage

`test_service_cancellation_requires_exact_current_operation` verifies at the owner boundary that a stale interrupt for a settled request leaves its busy successor untouched, even when both requests share the native conversation. `test_service_cancel_never_reaches_the_next_prompt` verifies the corresponding provider guard. `test_service_owner_persists_exact_outcome_without_replay` covers prewrite permission revocation, native connection loss after input, and caller response loss. `test_service_lost_owner_marks_current_attempt_uncertain` checks that stale evidence withdraws readiness and preserves the exact uncertain request.

The focused AG-UI, gateway, and manifest-preservation unit suites passed with 317 tests and one skip. They include recovery from older gateway queue evidence using the exact service record. Scoped Ruff, strict mypy, and `git diff --check` passed.

## Self-Hosted Qwen Plugin and Mail

Fixture `self-hosted-dsh-service-manager-f80e87216393` used DSH `0.2.2-rc.3`, `Qwen/Qwen3.8-27B-FP8`, and the `service` mode with backend `dsh_acp`. The fixture verified its private tmux socket. The in-process gateway exercised the local plugin dispatch boundary and the periodic notifier with a synthetic unread message in the fixture's filesystem mailbox.

The busy plugin delivery returned HTTP 409 and `not_sent`. The accepted plugin request `turn-bd2dad9611d9` returned `DSH04PLUGINQWEN` on native journal turn `1`. Mailbox request `gwreq-20261119-073244Z-f6ebfa46` completed on native journal turn `2` and appeared under the same request ID in usage. The notifier deferred while the mailbox request was active. Both requests held owner generation `ce5734ba-acd5-4534-804a-2bb35d0ae832`, service incarnation `9de00f8cbd9c4f848da84714259ff579`, and native conversation `01c06ffc-b915-47b5-b74c-807a88c5f5d6` with owner PID `3898585` and native PID `3898885`. Fixture cleanup returned `stopped_owned_identity`. Native journals and the scratch log remain private.
