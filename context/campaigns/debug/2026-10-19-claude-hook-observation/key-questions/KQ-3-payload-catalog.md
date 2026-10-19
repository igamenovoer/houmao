# KQ-3: Payload Catalog

Status: resolved (iteration 1, 2026-10-19). Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

What are the actual payload fields of the v1 event set at the installed version, and which correlation identifiers (`session_id`, `prompt_id`, `tool_use_id`) are present often enough to build on?

## Propositions

### P3.1 Prompt correlation exists

`prompt_id` (or an equivalent turn identifier) is present on `UserPromptSubmit` and on terminal events, or the catalog names its absence per event so the time-window fallback is exercised knowingly. Test: field inventory across S1-S7 captures.

### P3.2 Terminal payloads carry the designed fields

`Stop` carries `stop_hook_active`, `last_assistant_message`, `background_tasks`, `session_crons`; `StopFailure` carries `error`/`error_details`. Test: field inventory; record which are present, empty, or absent.

### P3.3 PermissionRequest fields

`PermissionRequest` carries `tool_name` and `tool_input` and lacks `tool_use_id` (as documented), and denial produces no companion event. Test: S3 capture, both allow and deny arms.

### P3.4 Compaction payloads

`PreCompact`/`PostCompact` fire on manual `/compact` with the documented fields, and turn identity survives compaction (armed `prompt_id` or equivalent continuity). Test: S4 capture.

### P3.5 SessionStart sources

`SessionStart.source` values observed across fresh launch, resume, and relaunch are cataloged (`startup`/`resume`/`clear`/`fork` or as found). Test: S1 vs S7 captures.

## Answer

Iteration 1, 2026-10-19. Full field inventory with per-session coverage, value classes, floor diff, and design deviations: [2026-10-19-hook-payload-catalog.md](../evidences/2026-10-19-hook-payload-catalog.md). Verdicts per proposition:

- **P3.1 partially confirmed.** `prompt_id` is present on every `UserPromptSubmit` and `Stop` and pairs within normal turns. Two caveats the reducer must encode: a queued prompt's `UserPromptSubmit` carries the in-flight turn's `prompt_id` (its own `Stop` has a fresh one), so queued correlation by `prompt_id` fails; and `SessionStart.prompt_id` appears only on the compact source. Evidence: [S7](../evidences/2026-10-19-s7-queue-resume.md), [S4](../evidences/2026-10-19-s4-compaction.md).
- **P3.2 partially confirmed.** `Stop` carries all four designed fields (`stop_hook_active`, `last_assistant_message`, `background_tasks`, `session_crons`) plus undocumented `effort` and `permission_mode`; `background_tasks` element shape is `{command, description, id, status, type}`. `StopFailure.error`/`error_details` unverified (event never fired; see KQ-2 P2.5). Evidence: catalog, [S5](../evidences/2026-10-19-s5-background-work.md).
- **P3.3 confirmed.** `PermissionRequest` carries `tool_name`, `tool_input`, `permission_suggestions`, `permission_mode`, and no `tool_use_id`; denial produces no companion event (no `PermissionDenied`, no `PostToolUseFailure`) and, stronger than documented, no `Stop`. Evidence: [S3](../evidences/2026-10-19-s3-permission-lane.md).
- **P3.4 confirmed.** `PreCompact`/`PostCompact` fire on manual `/compact` (`trigger: manual`, `custom_instructions: null`, 4.7 k-char `compact_summary`); `session_id` persists across compaction and per-turn `prompt_id` pairs stay intact; the compaction window has its own internal `prompt_id` and no `Stop`. Evidence: [S4](../evidences/2026-10-19-s4-compaction.md).
- **P3.5 confirmed.** `SessionStart.source` values cataloged: `startup` (all fresh launches), `compact` (S4), `resume` (S7, plus resume cost fields `context_tokens`, `estimated_cache_write_usd`, `prompt_cache_likely_expired`, `seconds_since_last_response`). `clear`/`fork` not exercised. Evidence: [S4](../evidences/2026-10-19-s4-compaction.md), [S7](../evidences/2026-10-19-s7-queue-resume.md).

Summary: the catalog is confirmed with documented deviations; the 2.1.296 floor payload is identical to 2.1.303 in the S1 exercise scope.

## Scope

Field-level catalog of the nine v1 events plus any unexpected events observed. Version differences between 2.1.303 and the 2.1.296 floor are recorded when floor capture is possible; otherwise the gap is named. Evidence: `evidences/` links added as produced.
