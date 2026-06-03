## Scan Notes

### Fixed in this change

| Pattern | Classification | Action |
|---|---|---|
| `assert target.controller is not None` in public managed-agent state, prompt, interrupt, gateway, mail, and turn helpers | Public operator-facing stale/degraded target issue | Replaced with `_require_live_local_controller(...)` and actionable stale/degraded diagnostics. |
| Generic memory direct-access error for non-local targets in `agents memory` helpers | Public operator-facing stale/degraded target issue | Routed through `_require_live_local_controller(...)` before local path resolution. |
| Root `_render_uncaught_exception()` fallback using `str(exc) or exc.__class__.__name__` | Public fallback issue | Replaced with explicit unexpected-internal-error wording and exception-class evidence. |

### Left unchanged

| Pattern | Classification | Rationale |
|---|---|---|
| `assert target.client is not None` after `_target_uses_pair_api(target)` or `target.mode == "server"` branches | Internal invariant after target resolution | Public target resolution constructs pair-backed targets with clients. If this invariant breaks, the new root fallback renders a reportable internal error instead of a bare class name. |
| `assert target.record is not None` inside stale/degraded stop and relaunch recovery helpers | Lifecycle-recovery invariant | Stale/degraded target resolution supplies records; these paths already recover or emit domain stop/relaunch diagnostics. |
| Broad `raise click.ClickException(str(exc))` conversions in project, credentials, native-agent, mailbox, and internals modules | Already-actionable or outside this change's local context | These conversions wrap domain parsers, filesystem/mailbox errors, or graph/native tooling errors that usually include path or command context. No specific bare implementation-level user report was found there during this scan. |
| Demo/test-only assertion messages | Non-public | They are not maintained `houmao-mgr` operator output. |
