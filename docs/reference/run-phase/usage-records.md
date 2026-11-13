# Agent Usage Records

Houmao records finalized turn accounting from structured client output and bound native session logs. The same record contract covers managed headless execution and native-observed turns whose provider identity and final outcome can be established. The source adapters read recorded counters; terminal text, character counts, and context occupancy do not establish usage.

## Public Queries

Use the attached gateway's `GET /v1/usage` route or the maintained passive-server route `GET /houmao/agents/{agent_ref}/usage`. Both accept `after` and `limit` and return the same versioned page. The default limit is 100 and the maximum is 500.

The passive server reads authoritative server-managed headless history when present. For other attached agents it forwards the query to the live gateway. It does not create another history or independently scan a remote gateway's provider files.

| Page Field | Meaning |
| --- | --- |
| `schema_version` | Public accounting schema version, currently 1. |
| `runtime_session_id`, `stream_id` | Runtime identity and the ledger's unique stream incarnation. |
| `capability` | Current source kinds, observed scopes, turn-recording support, and safe limitation reasons. |
| `collection` | Collection health and freshness, independent of already finalized history. |
| `records` | Bounded finalized records in insertion/finalization order. |
| `next_cursor` | Opaque position suitable for the next query, including at the current end. |
| `has_more` | Whether more finalized records existed in this read. |

Active turns stay outside `records`. A target can return readable older records while current collection is degraded. A never-supported target can return unavailable capability without a stream. Unsupported source capability is a normal response; unreadable or incompatible ledger storage returns an explicit storage error.

## Record Identity and Metrics

Each record identifies the agent, runtime session, registry generation, backend, provider session/turn where known, and Houmao accounting turn. `turn_origin` distinguishes managed attempts from directly observed native turns. Generated headless turn IDs are unique per attempt; repeated provider turn indices do not overwrite failed attempts.

The stable record ID is `usage-v1:<runtime_session_id>:<turn_id>`. Normal finalization and recovery use the same ID. A record also carries its completed, failed, or interrupted outcome and the original available execution timestamps.

Token measurements appear under `token_usage`: `input_tokens`, `output_tokens`, `cached_input_tokens`, `cache_write_input_tokens`, `reasoning_output_tokens`, and `total_tokens`. Each field is a metric object with a nullable `value`, `unit`, `availability`, `measurement_scope`, and optional `provenance`. Availability is `available`, `partial`, or `unavailable`; provenance identifies reported or derived measurements and their supporting sources/rule.

Missing and zero are different. A reported zero cache count is available with value zero. An omitted cache count is unavailable with a null value. Partial measurements retain the known amount and identify their incomplete coverage. Provider timing and client-reported cost have independent availability; absent prices are not estimated by this feature.

`token_semantics` describes whether cache counters are included in input and whether reasoning is included in output. A total is reported directly or derived only from a verified formula. For Codex, input already includes cached input and output includes reasoning. Adding those subsets again would overcount. Claude's qualified disjoint input/output/cache buckets can support a documented derived total when all required buckets are available.

Public `sources` contain opaque locators and accounting-only evidence. They exclude prompts, responses, tool content, private filesystem paths, credentials, and environment values. Private-subagent accounting defaults to `unknown`. Explicitly linked child measurements can appear as a parent-associated breakdown with overlap semantics; a child breakdown is not automatically added to an already inclusive parent total.

## Source Selection and Collection Boundaries

The collector binds the managed launch's isolated provider home to an exact provider session. Claude native logs live under the bound `CLAUDE_CONFIG_DIR/projects/`; Codex rollouts live under the bound `CODEX_HOME/sessions/` or supported archived sources. Kimi's qualified session logs live under its resolved data root, including `KIMI_CODE_HOME` for the supplied Qwen launcher.

At first attachment, the collector records the last complete source position and any verified cumulative baseline. Earlier conversation history may establish identity or a baseline but does not become new usage. Attaching during a turn produces incomplete coverage for that turn. Restart resumes the existing boundary rather than charging earlier records again.

Collection reads bounded batches of complete JSONL records. A partial trailing line waits for a later pass. Accepted observations and source progress commit in the same SQLite transaction. Truncation, replacement, and movement trigger identity/continuity validation, not a fresh charge for every reread request.

The adapter first creates scoped observations. The assembler selects a verified complete turn summary where available, otherwise distinct associated requests, and finally a verified cumulative delta where suitable. A summary and its requests do not both contribute to the same metric. Copies of one provider response in stdout, native logs, content blocks, or inherited fork history contribute once.

If two comparable cumulative totals are 1000 and 1600, the later increment is 600. Without a verified earlier baseline, the total 1600 is not assigned to the new turn. An unexplained decrease or counter epoch change leaves affected metrics partial or unavailable.

TUI support depends on structured turn identity and terminal evidence, not the backend label. Hooks can associate provider session/turn identities and lifecycle facts, but they do not measure tokens. A session-only source reports that limitation instead of assigning its total to an arbitrary prompt.

## Finalization, Storage, and Recovery

The private ledger lives at `<session-root>/usage/records.sqlite3`, separately from gateway queue storage. It stores source bindings/checkpoints, provisional observations, pending turns, and immutable final records. Each first insertion receives a finalization sequence. Equivalent replay is a no-op; conflicting repeated accounting fails explicitly rather than silently changing consumed history.

Headless execution persists `usage-start.json` and `usage-final.json` alongside the unique turn's artifacts. Start evidence snapshots the original agent/runtime identities, registry generation, and source boundary. Final evidence retains the original outcome, timing, and source cutoff. Recovery uses those facts even if the agent has since relaunched under a new generation.

Native-observed turns retain equivalent durable pending/terminal state. Evidence beyond a finalized cutoff cannot silently enrich its immutable record. A controller timeout while the provider still runs leaves accounting pending. A terminal headless attempt without usage still produces its lifecycle record with unavailable token metrics.

History reads use the ledger and do not synchronously scan provider logs or acquire the terminal-mutation lock. Startup and recorder recovery reconcile missing finalization from durable facts. Reconciled late records receive later sequence positions regardless of their original start time.

## Polling and Cursor Lifetime

Always retain `next_cursor`, including when `has_more` is false or `records` is empty. The cursor represents the last returned finalization sequence, not a turn timestamp. An initially empty queryable stream returns a sequence-zero cursor that can retrieve its first future record.

A controller's polling loop follows this order:

1. Query a bounded page using its saved cursor.
2. Apply each record idempotently using `record_id` as its accounting key.
3. Persist the returned `next_cursor` after accepting that page.
4. Fetch immediately again if `has_more` is true; otherwise wait for the next polling interval while retaining the cursor.

A late-finalizing older turn appears after the saved sequence. Provider-chat reset preserves the runtime stream but creates a new source binding or counter epoch. Relaunch preserves older history and its original generation. A new runtime or replacement ledger has a distinct stream incarnation, so a cursor from another stream is rejected with validation error rather than silently resetting the reader.

## Qualified Provider Evidence

Sanitized exact-version fixtures are stored under `tests/fixtures/agent-usage-records/`. The qualification captures used the supplied change-local launchers against H20 SGLang `Qwen/Qwen3.8-27B-FP8`. Each fixture includes the running client version, upstream protocol/model, reference revision, and two completed/resumed turns. Identity values are pseudonyms; prompt and response bodies are absent.

| Client and Fixture | Qualified Findings | Remaining Limits |
| --- | --- | --- |
| Claude Code 2.1.323, `claude-2.1.323-qwen.json` | `result.usage` is invocation-scoped; native assistant copies retain final counters and `stop_reason: end_turn`. `total_cost_usd` and `duration_api_ms` are session-cumulative, while `duration_ms` is invocation-scoped. Turn cost/API duration require a comparable baseline. | Client-reported cost is preserved as reported accounting, not asserted to equal an upstream invoice. Private-subagent inclusion remains unknown. |
| Codex CLI 0.167.2, `codex-0.167.2-qwen.json` | Native response records identify the request and provider turn. `token_count` repeats that request; exec `turn.completed.usage` is cumulative on resume. Cache and reasoning counters are included subsets. | Older formats require their qualified fallback rules; unknown/reset baselines remain explicit. Private-subagent inclusion remains unknown. |
| Kimi Code 2.6.0, `kimi-2.6.0-qwen.json` | Native `turn.prompt` and `turn.ended` identify turns. `usage.record` contains request increments and `step.end` repeats them. Structured headless stdout has no usage. | Qwen omitted `inputCacheRead`, so cached input and a disjoint total remain unavailable. Non-turn scope is not assumed cumulative. Private-subagent inclusion remains unknown. |

Qualification is specific to the tested client/version and upstream configuration. Native client version declarations are retained in observation checkpoints and public source provenance. An explicitly unqualified version preserves allowlisted raw counters with unknown scope and inclusion rules, so those counters cannot become turn charges. Versionless records use the recognized format profile established by these captures; an unrecognized shape produces no accounting observation. Source-format compatibility does not authorize filling missing measurements or inferring unsupported aggregation behavior. Durable tests consume retained fixtures and do not require the ignored source checkouts, live service, or OpenSpec change-local launch scripts.

Claude hook `prompt_id` and native user-message `uuid` belong to different namespaces in the qualified client. The collector uses hooks to discover Claude session identity, then uses native user/assistant lifecycle to establish native turns. It does not create another record from an unmapped hook-only turn or associate a managed submission by similar timing.

The [managed qualification procedure](../../../scripts/qualification/agent-usage/README.md) documents unattended Houmao-manager launches, public usage-page checks against raw accounting evidence, and the successful headless/TUI matrix for all three clients. It uses fresh private homes and retains disposable captures under ignored scratch directories.
