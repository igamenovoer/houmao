## 1. Gateway Audit Contract

- [x] 1.1 Extend gateway-owned notifier auditing with a dedicated `gateway_notifier_audit` table in `queue.sqlite` so each enabled poll cycle records structured decision data with unread-set summary, eligibility inputs, and enqueue-or-skip outcome.
- [x] 1.2 Add or update gateway unit and integration coverage for audit-row insertion and querying, unread-set batching, duplicate-reminder suppression, and busy-skip auditing.

## 2. Demo Pack Scaffold

- [x] 2.1 Create `scripts/demo/gateway-mail-wakeup-demo-pack/` with tracked inputs, `README.md`, `run_demo.sh`, `expected_report/report.json`, and pack-local helper scripts for sanitization, verification, and inspection.
- [x] 2.2 Add pack-local helper logic for demo-owned workspace setup, launcher-managed loopback CAO handling, persistent demo state, and mailbox delivery payload generation through the managed mailbox script boundary, while allowing only narrow reuse of already-stable repository helpers if they land first.

## 3. Automatic And Manual Wake-Up Flows

- [x] 3.1 Implement the automatic workflow that starts one mailbox-enabled session, attaches the gateway, enables notifier polling, waits for idle status, injects the wake-up mail, and waits for the demo-owned output file.
- [x] 3.2 Implement the manual workflow for single-message injection from `--body-content` or `--body-file`, plus burst-message injection against the same live session.
- [x] 3.3 Implement inspection and verification steps that read durable notifier audit history directly from the gateway root, capture notifier status, queue or event artifacts, mailbox-local unread state, and output-file artifacts, and reduce raw notifier audit rows to stable outcome-summary evidence in the sanitized demo report.

## 4. Docs And Validation

- [x] 4.1 Write the tutorial README in the repository’s API-tutorial style, including unread-set semantics, automatic flow, manual flow, verification, snapshot refresh, appendix sections, and the distinction between compact notifier status and detailed durable audit history.
- [x] 4.2 Add or update doc links or operator guidance that point readers from gateway reference material to the new wake-up demo pack and document the SQLite notifier audit surface as the place to inspect detailed per-poll decisions.
- [x] 4.3 Run targeted tests for SQLite-backed gateway notifier auditing, summary-style report sanitization, and the new demo helpers, then run `pixi run openspec validate --strict --json --type change add-gateway-mail-wakeup-demo-pack`.
