## Context

The gateway already writes a stable human-oriented running log at `<session-root>/gateway/logs/gateway.log`, keeps durable queue and notifier audit state in `queue.sqlite`, and exposes status through `state.json` plus HTTP routes. That is enough for live tailing and for notifier-specific auditing, but it does not reliably answer postmortem questions such as whether a malformed `/v1/mail/send` request was rejected before route handling, whether a mailbox operation reached filesystem delivery, or whether the same warning repeated hundreds of times while a caller ignored HTTP failure status.

The diagnostic logging feature should live inside the gateway because the gateway is the boundary that sees local HTTP requests, validation failures, mailbox facade operations, queue/control decisions, and gateway-owned notifier or reminder loops. It must also respect the existing repository posture that runtime logs are inspectable but cleanup-sensitive, while `queue.sqlite`, `events.jsonl`, `state.json`, and manifest files remain durable gateway state.

## Goals / Non-Goals

**Goals:**

- Provide opt-in rotating diagnostic log files under the gateway-owned log directory.
- Capture enough structured evidence to diagnose HTTP validation failures, mailbox facade outcomes, queue/control errors, notifier/reminder warnings, and gateway-side exceptions.
- Record route-level failures that happen before endpoint handlers run, including FastAPI request validation errors.
- Redact message bodies, raw prompt text, auth material, and attachment contents by default.
- Bound disk usage with rotation and backup limits.
- Suppress consecutive repeated warning/error diagnostics by semantic key and emit suppressed-count summaries.
- Keep `gateway.log` as the stable tail-friendly running log and keep existing durable artifacts authoritative for queue/status/recovery.

**Non-Goals:**

- Do not introduce remote telemetry, external log shipping, or a new service dependency.
- Do not make diagnostic logging mandatory for normal gateway operation.
- Do not replace `queue.sqlite`, notifier audit rows, `events.jsonl`, or `state.json` as machine-readable state contracts.
- Do not log mailbox bodies, raw prompts, attachment contents, credentials, bearer tokens, cookies, or environment secrets by default.
- Do not promise a long-term stable schema for every diagnostic payload field; the stable contract is the presence, redaction boundary, rotation behavior, and event categories.

## Decisions

### Add a separate opt-in diagnostic logger

Diagnostic entries should go to a separate path such as `<session-root>/gateway/logs/diagnostics/gateway-diagnostic.log` rather than expanding `gateway.log`. The existing log remains optimized for humans tailing live behavior, while diagnostic logs can be JSONL, bounded, and richer without making ordinary logs noisy.

Alternative considered: put everything in `gateway.log`. This is simpler, but it conflicts with the current role of `gateway.log` as a compact tail surface and makes structured postmortem parsing brittle.

Alternative considered: store all diagnostics in `queue.sqlite`. That would make querying easier but would turn an opt-in cleanup-sensitive diagnostic surface into durable gateway state, which is not the right retention posture for potentially sensitive operational traces.

### Configure diagnostics through gateway desired/runtime config

The opt-in switch and rotation settings should be represented in gateway config plumbing, with conservative defaults: disabled by default, bounded max bytes, bounded backup count, and redaction enabled. Runtime launch and attach paths can preserve or update those desired settings the same way they already persist listener and TUI tracking preferences.

The minimal useful configuration is:

- `enabled`
- `max_bytes`
- `backup_count`
- optional `level` or event-category filter if implementation wants it

Alternative considered: environment variables only. Environment variables are useful for bootstrap tests, but persisted desired config makes same-session restarts and attach flows easier to reason about.

### Capture validation failures at the HTTP boundary

Some of the most important failures never reach methods such as `send_mail()` because FastAPI validates request bodies first. Diagnostic logging therefore needs middleware and/or exception handlers around `create_app()`, not only calls inside `GatewayServiceRuntime`. Route handlers should still add operation-specific context after validation succeeds.

For issue-style mailbox investigations, the useful entries are:

- request received/completed with method, path, status, duration, and request id,
- validation error with normalized error locations and messages,
- mailbox operation started with transport and redacted participant metadata,
- mailbox operation succeeded with generated message id and recipient count,
- mailbox operation failed with HTTP status, error class/category, message id when known, and repair hint when applicable.

### Redact by construction

Diagnostic entries should be built from explicit safe fields, not by dumping request or response objects. Mailbox message bodies, raw prompts, memory page contents, auth headers, cookie headers, attachment contents, and local secret paths should not be emitted by default. Recipient and sender addresses are acceptable because mailbox routing itself depends on them and issue triage often needs them; if later sensitivity demands change, they can be hashed behind a separate option.

Alternative considered: log full payloads with ad hoc redaction. That is easier initially but fragile because new fields can accidentally become logged before redaction is updated.

### Deduplicate consecutive warning/error diagnostics by semantic key

The diagnostic logger should coalesce only consecutive warning/error entries with the same semantic key. The semantic key should ignore volatile values such as timestamp, request id, duration, and generated message ids, while preserving event code, route, HTTP status, error category, and normalized validation field paths. The first occurrence is written normally. Repeats increment an in-memory counter. When a different entry arrives, rotation/shutdown occurs, or the logger is flushed, the logger writes a summary entry with the suppressed count.

Alternative considered: time-window rate limiting. Existing `gateway.log` uses coarse rate-limited logging for some notifier messages, but postmortem diagnostics are easier to interpret when consecutive duplicate suppression preserves event ordering and exact repeat counts.

### Treat diagnostic logs as cleanup-sensitive runtime logs

Diagnostic logs should live under `gateway/logs/` so existing cleanup concepts can classify them as runtime log artifacts. Cleanup must preserve durable gateway state such as manifests, `queue.sqlite`, `events.jsonl`, and `state.json`; diagnostic logs do not become durable state merely because they are useful for debugging.

## Risks / Trade-offs

- [Risk] Diagnostic logs accidentally expose sensitive agent content. -> Mitigation: build entries from explicit safe fields, add tests for redaction boundaries, and avoid dumping raw request or response bodies.
- [Risk] Operators expect diagnostics to always exist. -> Mitigation: document that this is opt-in and expose the enabled state through status or inspectable config.
- [Risk] Rotation loses old evidence before a postmortem. -> Mitigation: use conservative defaults and make max size plus backup count configurable.
- [Risk] Dedup hides important repeated failures. -> Mitigation: deduplicate only consecutive warning/error entries with the same semantic key and emit explicit suppressed-count summaries.
- [Risk] Middleware logging duplicates operation-specific entries. -> Mitigation: keep HTTP entries route/status oriented and operation entries domain-specific.

## Migration Plan

No on-disk migration is required. Existing gateway roots continue without diagnostic logging enabled. New config fields should default to disabled when absent.

Implementation can ship as a normal code update. Rollback leaves existing diagnostic files as ordinary runtime log artifacts; cleanup commands may remove them after the session is stopped.

## Open Questions

- Should the first implementation expose diagnostic logging only through stored desired config and launch/attach options, or also through a live gateway HTTP control route?
- Should sender and recipient addresses remain plain text in diagnostic logs, or should the first implementation support an address-hashing mode?
