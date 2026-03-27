## 1. Server-Backed Lifecycle

- [x] 1.1 Replace the pack's demo-owned CAO launcher setup and persisted CAO metadata with demo-owned `houmao-server` startup, shutdown, and server-state artifacts under the selected demo output root.
- [x] 1.2 Update tracked parameters and the session start flow so the live mailbox-enabled session launches with `backend=houmao_server_rest` and persists enough managed-agent identity to target the same session across follow-up commands.
- [x] 1.3 Stage the runtime-owned mailbox skill documents into the copied dummy-project workdir during provisioning and fail clearly if that project-local mailbox skill surface cannot be prepared.

## 2. Control And Reporting

- [x] 2.1 Switch gateway attach, notifier control, inspection targeting, and stop behavior to the server-backed managed-agent control path while keeping manual mail injection on the managed delivery-script boundary.
- [x] 2.2 Replace CAO-terminal idle detection with server-first readiness checks plus gateway-status fallback before automatic mail injection.
- [x] 2.3 Revise inspect, report, sanitize, and expected-report handling so the golden contract records server-backed lifecycle and managed-agent evidence instead of CAO-specific launcher and terminal artifacts.

## 3. Docs And Regression Coverage

- [x] 3.1 Update `scripts/demo/gateway-mail-wakeup-demo-pack/README.md` and tracked inputs to teach the demo-owned `houmao-server` lifecycle, `houmao_server_rest` session backend, post-launch attach model, and project-local mailbox skill layout.
- [x] 3.2 Update `tests/unit/demo/test_gateway_mail_wakeup_demo_pack.py` and related fixtures or doubles so regression coverage detects drift back to CAO-owned defaults, missing mailbox skill staging, and report-contract drift.
- [x] 3.3 Run targeted validation for the demo-pack tests and `openspec validate --strict --type change migrate-gateway-mail-wakeup-demo-pack-to-houmao-server`.
