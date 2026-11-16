# Qualification Evidence

This change was qualified on 2026-11-14 against the local Stalwart 0.15.5 service documented in [SERVICES.md](../../../../SERVICES.md). The source reference checkout was 0.16.26; the separate `v0.15.5` Git tag was inspected for release-specific sending-identity behavior. No result below establishes capacity for 100 agents or millions of retained messages.

## Normal-Account Protocol Round

The [client qualifier](../../../../scripts/qualification/stalwart-mail/client.py) used two explicitly selected normal accounts. It validated the selected account and sending identity, listed body-free metadata, fetched selected content, sent a unique test message to the other account, marked it read, replied, and archived both received messages. Both submissions returned confirmed receipts. The parent became read and answered, and archive removed inbox membership. Email changes, query changes, and a fresh connection accepting the previous email checkpoint also passed.

The representative run submitted two messages, used 41 JMAP methods across two accounts, and took approximately 0.182 seconds. These measurements describe this local sandbox run only. The sanitized report is `/tmp/houmao-mail-02-qualification/client.json`; the durable procedure and fixture limitations are in the [qualification README](../../../../scripts/qualification/stalwart-mail/README.md).

Sending-identity and Archive-folder initialization were separate account setup actions. Houmao attachment read only the selected normal-account credential. It performed no domain/account provisioning, required no management credential, and changed no provider password. Stalwart 0.15.5 rejects a new `.test` sending identity because its validator requires a recognized public suffix. The local fixture uses reserved `example.com` aliases. Self-delivery can deduplicate against the sender's Sent object, so real delivery checks used the second account.

## Live Binding and Reminder Runtime

The [runtime qualifier](../../../../scripts/qualification/stalwart-mail/runtime.py) used real Stalwart calls, an in-process HTTP ASGI gateway fixture, and a fake body subprocess. Generated state and credential snapshots stayed outside the checkout. Attachment started from an empty mail configuration and preserved the internal agent ID, body PID, conversation marker, and backend state.

Attach, metadata-only list, same-account refresh, epoch-changing reconnect, gateway reconstruction with persisted sync recovery, and online detach all passed. The same inbox work produced exactly two admitted reminders across two due interval cycles. Repeating a cycle produced `dedup_skip`; the body received the two actual prompts. The process's measured peak RSS was 123,812 KiB, including the Python test fixture and application imports. This is not a per-agent memory estimate.

The runtime fixture explicitly moved its unique self-created test item into Inbox because self-delivery can deduplicate. Its cleanup archived only that item. The sanitized report is `/tmp/houmao-mail-02-runtime-01/runtime-report.json`. Deterministic integration additionally exercises a real loopback Uvicorn gateway/provider, rejected credentials, endpoint failure, source rotation, replacement races, and old queued reminder cancellation; see [runtime integration tests](../../../../tests/integration/mailbox/test_online_runtime_contract.py).

## Bounded Observation Measurements

The [read-only observer qualifier](../../../../scripts/qualification/stalwart-mail/observe.py) ran five cycles for one normal account, using an external private SQLite cache. It observed a two-item eligible sample; it did not enumerate retained history to infer a total.

| Measurement | Observed Value |
| --- | --- |
| HTTP requests | 15 |
| HTTP request body bytes | 3,987 |
| HTTP response body bytes read | 14,134 |
| Connection initialization JMAP methods | 2 |
| Observation JMAP methods across five cycles | 11 |
| Methods per cycle | 4, 4, 1, 1, 1 |
| Cycle latency p50 | 0.012861 seconds |
| Cycle latency p95 | 0.027648 seconds |
| Process peak RSS | 97,869,824 bytes |
| Bootstrap to first idle view | 0.164305 seconds, two cycles |

Byte counts exclude HTTP headers, TLS framing, and unread error bodies. RSS includes the standalone interpreter and imported modules. Reminder counts belong to the separate gateway runtime result above; this raw observer has no scheduler or body. The sanitized report is `/tmp/houmao-mail-02-observe-01/report.json`.

The [load plan](../../../../docs/reference/mailbox/operations/stalwart-qualification.md) specifies retained archive and active inbox sizes separately, 100-agent targets, request/byte/latency/RSS measurements, busy-body reminders, reconnect, stale-state recovery, and failure criteria. Large-scale and large-backlog runs remain unexecuted. Deterministic wire tests cover intermediate checkpoints, failures, budget yields, stale-state rebase, and bounded sample behavior.

## Repository Checks

Final checks after the role-policy and prompt-effect race fixes:

| Check | Result |
| --- | --- |
| `pixi run test -q --tb=line` | 3,651 passed; 14 skipped; 10 existing FastAPI/httpx deprecation warnings; 70.55 seconds |
| Affected mailbox plus gateway/mailbox/registry runtime integration suites | 29 passed; one matching deprecation warning; 18.43 seconds |
| `pixi run lint` | Passed |
| `pixi run typecheck` | Passed for 449 source files |
| Changed Python formatting | 153 changed Python files passed the final formatting check |
| `git diff --check` | Passed |
| Strict change OpenSpec validation | Passed with zero issues |

The final sync/wire policy-race regression subset passed 68 cases. Real gateway integration includes the exact origin-check-to-submit race and a started-effect retirement deadline. The final repeated live runtime run also passed after effect leases, preserving body PID/conversation, account checkpoint recovery, and two due reminder admissions. Its sanitized report is `/tmp/houmao-mail-02-runtime-02/runtime-report.json`; measured peak RSS was 125,564 KiB.

Local aggregate logs are `tmp/mail-02-unit-qualified.txt`, `tmp/mail-02-integration-qualified.txt`, `tmp/mail-02-typecheck-qualified.txt`, `tmp/mail-02-lint-qualified.txt`, and `tmp/mail-02-validation-qualified.json`. Raw reports and logs remain private local artifacts; tests and qualification tools provide the durable reproduction path. No real credentials are present in tracked examples, reports, profiles, or source files.
