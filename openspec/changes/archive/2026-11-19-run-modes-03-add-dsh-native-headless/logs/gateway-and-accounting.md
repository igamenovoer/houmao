# Gateway, CLI Events, and Accounting

The local DeepSeek Harness checkout at `39163dd30f703a79079e2d2446545cff3c453738` emits a `session` frame before accepting native input. Its `final` frame follows the awaited native session flush. Houmao projects the frame's session ID and reason separately from managed completion. The bridge establishes managed completion only when the exact native handoff, journal, final frame, and process exit agree.

The gateway resolves conversation selection after reserving the current owner slot. A fresh DSH dispatch controller reads the latest saved native session before running the next worker. The old per-turn ACP backend is no longer a maintained headless gateway target. Its standalone execution and accounting tests retain their original transport.

The usage collector reads DSH's v4 journal and preserves separately billed retry attempts. It confirms CLI handoff against the worker's recorded birth token, then matches the admitted message with its native claim. Aggregated step summaries in CLI stdout do not add a second billing source. Crash recovery leaves a zero exit pending until the exact native closure record is available.

Only the CLI's next-invocation skills boundary is qualified. The common-plugin refresh API covers skills and MCP together, so it reports unsupported for that whole scope. Its observation still identifies the skills boundary and leaves MCP unsupported. Checking or refreshing that scope does not launch a native worker or rewrite the private home.

## Controlled Verification

- **217 passed** across headless output, DSH journal accounting, DSH gateway admission, native refresh, and gateway support unit suites. The CLI stream cases cover identity mismatch, incomplete and malformed lines, bounded redaction, and incomplete native reasons.
- **68 passed** in a focused rerun that adds active and idle native refresh observations and verifies CLI journal recovery and usage deduplication.
- **94 passed** across the historical native ACP execution fixture and adjacent Web, gateway access, owner admission, and refresh suites. The run reported one dependency deprecation warning.
- **3 passed** in the migrated RC.3 gateway and passive integration suite against a controlled local Messages endpoint. It covered busy-slot refusal, two workers continuing one native session, passive status recovery and raw NDJSON, a CCCC event, and repeated reminders for unchanged unread filesystem mail.
- **3 passed** in reconstructed native control integration. The exact worker was stopped or interrupted from a separate controller. The gateway's durable queued request reported the interrupted outcome with owner-process evidence. Each case produced one provider request and recorded interrupted usage.
- **2 passed** in the maintained refresh and relaunch integration. The cases exercised explicit new and exact resume policies. Observation and refresh preserved native role, profile, session, and journal bytes before relaunch.
- Scoped Ruff, strict mypy, and `git diff --check` passed.

All managed integration cases used isolated tmux sockets and synthetic provider credentials. Live Qwen fixture results are recorded separately in this change's implementation log.
