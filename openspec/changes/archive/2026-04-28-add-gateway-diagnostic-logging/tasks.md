## 1. Configuration And Storage Layout

- [x] 1.1 Add gateway diagnostic logging configuration models with disabled-by-default behavior, rotation size, and backup-count validation.
- [x] 1.2 Persist diagnostic logging settings through gateway desired-config load/write paths without breaking existing desired-config files.
- [x] 1.3 Extend gateway path helpers with a dedicated diagnostic log directory and active diagnostic log path under `gateway/logs/`.
- [x] 1.4 Thread diagnostic logging settings through gateway launch and attach startup paths so enabled settings survive gateway restarts.

## 2. Diagnostic Logger Core

- [x] 2.1 Implement a gateway diagnostic logger that writes structured line-oriented entries only when enabled.
- [x] 2.2 Implement bounded file rotation using configured max bytes and backup count.
- [x] 2.3 Implement explicit safe-field entry construction that avoids raw request/response object dumps.
- [x] 2.4 Implement consecutive warning/error deduplication by semantic key with suppressed-count summary flushing.
- [x] 2.5 Flush pending dedup summaries on gateway shutdown and before rotation-sensitive closeout.

## 3. Gateway Instrumentation

- [x] 3.1 Add FastAPI middleware and/or exception handlers to log request completion and request-body validation failures at the HTTP boundary.
- [x] 3.2 Instrument mailbox facade operations to log safe start, success, and failure diagnostics for send, post, reply, list, read, mark, move, and archive.
- [x] 3.3 Include repair guidance in mailbox diagnostic failures when the underlying error indicates repairable mailbox-local state.
- [x] 3.4 Instrument queue/control, reminder, and notifier warning/error paths that currently rely only on `gateway.log` when diagnostic logging is enabled.
- [x] 3.5 Ensure diagnostic logging failures never make gateway HTTP routes or worker loops fail.

## 4. Cleanup And Documentation

- [x] 4.1 Update runtime log cleanup planning so gateway diagnostic logs are removable log artifacts while durable gateway files remain preserved.
- [x] 4.2 Update gateway contract, operations, internals, and troubleshooting docs with diagnostic logging behavior, paths, redaction, dedup, and rotation guidance.
- [x] 4.3 Update the system-files reference to list gateway diagnostic logs with cleanup-sensitive retention semantics.
- [x] 4.4 Document how diagnostic logging differs from `gateway.log`, `events.jsonl`, `queue.sqlite`, and notifier audit records.

## 5. Validation

- [x] 5.1 Add unit coverage for disabled-by-default diagnostic logging and enabled diagnostic file creation.
- [x] 5.2 Add unit coverage for HTTP validation failure capture without raw request body logging.
- [x] 5.3 Add unit coverage for mailbox facade success and failure diagnostic entries with body, prompt, auth, and attachment redaction checks.
- [x] 5.4 Add unit coverage for consecutive warning/error deduplication and suppressed-count summary flushing.
- [x] 5.5 Add unit coverage for rotation limits and cleanup classification of diagnostic log files.
- [x] 5.6 Run focused gateway, mailbox, cleanup, docs/spec validation, lint, and typecheck commands needed for the touched surfaces.
