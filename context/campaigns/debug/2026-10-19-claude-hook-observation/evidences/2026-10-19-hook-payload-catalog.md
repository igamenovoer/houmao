# Payload Catalog: Claude Hook v1 Event Set (2.1.303 + 2.1.296 floor)

Date: 2026-10-19. Built from the raw `events.ndjson` streams of iteration 1 (not from memory). Sources: S0, S1, S2, S3, S4, S5, S6, S7 at 2.1.303, plus the S1 floor repeat at 2.1.296. Session coverage per event is noted per field. Value classes: str, int, float, bool, array, object, null. Structure only; no credential material. Session-authored prompt text is quoted where it carries structure (ghost turns, slash commands).

Convention: every payload also carries the emitter-added stamps `received_at_utc`, `emitter_sequence`, `channel_generation` on the SessionStart command path (nested inside `provider_event`); these are harness stamps, not provider fields, and are excluded from the tables. Collector envelope fields (`sequence`, `received_at_utc`, `channel_generation`, `via`) sit one level up and are also excluded.

## SessionStart

Observed in: S0, S1, S2, S3, S4 (x2), S5, S6, S7 (x2), floor S1. `via: http` (emitter POST) in every case; the file fallback was never needed live.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | all | `SessionStart` |
| `session_id` | str | all | UUID; identical across compaction and resume |
| `source` | str | all | values observed: `startup` (fresh launches), `compact` (S4 mid-compaction restart), `resume` (S7 relaunch). `clear`/`fork` not exercised |
| `model` | str | all | `deepseek-flash[1m]` (launcher-pinned id, not the friendly name) |
| `cwd` | str | all | session workdir |
| `transcript_path` | str | all | `~/.claude/projects/...` transcript |
| `prompt_id` | str | S4 only | present only on the `source: compact` SessionStart; the internal compaction turn id |
| `context_tokens` | int | S7 only | resume-source only (55,846 in S7) |
| `estimated_cache_write_usd` | float | S7 only | resume-source only (0.349 in S7) |
| `prompt_cache_likely_expired` | bool | S7 only | resume-source only (`false`) |
| `seconds_since_last_response` | int | S7 only | resume-source only (2 in S7) |

The four resume-only fields are the resume cost fields (design 5.3 mentions resume/fork cost fields in a later version; they are present at 2.1.303). Undocumented in the v1 design: all of `prompt_id`, `context_tokens`, `estimated_cache_write_usd`, `prompt_cache_likely_expired`, `seconds_since_last_response`.

## UserPromptSubmit

Observed in: all sessions. Counts: S1 x2, S3 x2, S5 x2, S6 x2, S7 x2, one each in S0/S2/S4/floor.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | all | |
| `session_id` | str | all | |
| `cwd` | str | all | |
| `transcript_path` | str | all | |
| `prompt` | str | all | verbatim submitted text; three shapes seen: human prompt (quoted in evidence docs), ghost turn `<task-notification>...</task-notification>` (S5), slash-command text (`/exit` becomes a prompt on 2.1.303, pre-expansion per design 5.3) |
| `prompt_id` | str | all | see correlation caveat below |
| `permission_mode` | str | all | `bypassPermissions` (skip-permissions lane), `default` (manual lane). Undocumented in design section 1 |

Design-promised but absent: `source` (optional in design; never present in any session).

Correlation caveat (S7): a queued prompt's `UserPromptSubmit` fires at type time and carries the **in-flight turn's** `prompt_id`; the queued turn's own `Stop` carries a **fresh** `prompt_id`. Queued UPS-to-Stop correlation by `prompt_id` fails; correlate by sequence adjacency.

## Stop

Observed in: S0, S1 (x2), S2, S3, S4 (x2), S5 (x2), S7 (x2), floor (x2). Not observed in S6 (Esc arm: none fired).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | all | |
| `session_id` | str | all | |
| `cwd` | str | all | |
| `transcript_path` | str | all | |
| `prompt_id` | str | all | pairs with the turn's UserPromptSubmit for normal turns |
| `permission_mode` | str | all | undocumented in design section 1 |
| `stop_hook_active` | bool | all | `false` everywhere observed |
| `last_assistant_message` | str | all | final assistant text; empty only if interrupted |
| `background_tasks` | array | all | element shape `{command: str, description: str, id: str, status: str, type: str}`; non-empty while tasks run (`status: "running"`), drained to `[]` after completion (S5) |
| `session_crons` | array | all | always `[]` in these sessions |
| `effort` | object | all | `{level: str}` (`{level: "max"}`); undocumented in design section 1 |

## PermissionRequest

Observed in: S3 only (x3: two Write calls, one Bash call). All on the manual-permission lane.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name` | str | S3 | |
| `session_id` | str | S3 | |
| `cwd` | str | S3 | |
| `transcript_path` | str | S3 | |
| `prompt_id` | str | S3 | the blocked turn's id |
| `permission_mode` | str | S3 | `default` |
| `effort` | object | S3 | `{level: "max"}`; undocumented |
| `tool_name` | str | S3 | `Write`, `Bash` |
| `tool_input` | object | S3 | tool args, e.g. `{content: str, file_path: str}` for Write |
| `permission_suggestions` | array | S3 | e.g. `[{type: "setMode", destination: "session", mode: "acceptEdits"}, {type: "addDirectories", destination: "session", directories: ["/tmp"]}]` |

As documented: **no `tool_use_id`** on this event (confirmed). Denial produced no companion event of any kind (no `PermissionDenied`, no `PostToolUseFailure`), and additionally no `Stop` (S3 evidence).

## PreCompact

Observed in: S4 only. `trigger: "manual"` (typed `/compact`).

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name`, `session_id`, `cwd`, `transcript_path`, `prompt_id` | str | S4 | `prompt_id` is the internal compaction turn id, shared with PostCompact |
| `trigger` | str | S4 | `manual` |
| `custom_instructions` | null | S4 | present but null for a bare `/compact` (no compaction instructions configured); catalog as nullable |

## PostCompact

Observed in: S4 only.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name`, `session_id`, `cwd`, `transcript_path`, `prompt_id` | str | S4 | same internal `prompt_id` as PreCompact |
| `trigger` | str | S4 | `manual` |
| `compact_summary` | str | S4 | 4,717 to 4,774 chars across the two S4 runs; the compaction summary text |

The compaction window emits no `Stop` for the internal compaction turn; `PostCompact` is the maintenance-terminal.

## PostToolUse

Observed in: S3 (x2), S4, S5. Not fired in tool-free turns (S0/S1/S2/S6/S7/floor), as expected.

| Field | Class | Seen in | Notes |
| --- | --- | --- | --- |
| `hook_event_name`, `session_id`, `cwd`, `transcript_path`, `prompt_id` | str | S3, S4, S5 | |
| `permission_mode` | str | S3, S4, S5 | |
| `effort` | object | S3, S4, S5 | `{level: "max"}`; undocumented |
| `tool_name` | str | S3, S4, S5 | `Read`, `Write`, `Bash` |
| `tool_use_id` | str | S3, S4, S5 | present here (unlike PermissionRequest) |
| `tool_input` | object | S3, S4, S5 | tool args |
| `tool_response` | object | S3, S4, S5 | Write: `{type: "create", filePath, structuredPatch, ...}`; Bash background: `{backgroundTaskId, interrupted, ...}` |
| `duration_ms` | int | S3, S4, S5 | 29 to 44 ms in S3 |

## Subscribed but Never Observed

| Event | Why never observed |
| --- | --- |
| `StopFailure` | No safe fault lane exists (relay/network cuts out of bounds). P2.5 declared unreachable; missing control: a session-scoped API-fault injector. |
| `PostToolUseFailure` | No tool-failure arm in the matrix; the S6 Esc interrupt (the plausible trigger) produced no events at all. |
| `SessionEnd` | Deliberately not subscribed (v1 = 9 events; design tiers it P2 optional). Absence recorded after exit in S1, S3, and the floor run. |

## 2.1.296 Floor Diff

Field inventory for `SessionStart`, `UserPromptSubmit`, and `Stop` is **identical** between 2.1.303 and the 2.1.296 floor (S1 repeat, `evidences/2026-10-19-floor-2-1-296-s1-repeat.md`), including the undocumented `effort`, `permission_mode`, and `session_crons` fields. The floor adds nothing and removes nothing observable in the S1 exercise scope.

## Summary of Design Deviations

Observed but undocumented in design section 1: `Stop.effort`, `UserPromptSubmit.permission_mode`, `Stop.permission_mode`, `PermissionRequest.effort`, `PostToolUse.effort`, `SessionStart.prompt_id` (compact), the four resume cost fields, the ghost-turn `<task-notification>` prompt shape, and the `background_tasks` element shape (now recorded above). Documented but absent: `UserPromptSubmit.source` (optional, never sent). Documented but never exercised: `StopFailure.error`/`error_details`, all `PostToolUseFailure` fields, `PreCompact.custom_instructions` (present-null).
