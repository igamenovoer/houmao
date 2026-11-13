# Tasks

## 1. Provider Evidence and Accounting Models

- [ ] 1.1 Capture sanitized Claude and Codex headless/native-log fixtures using the default fixture auth bundles and local source references; record running binary versions separately from reference revisions, and verify resumed scope, request/turn identities, cache/reasoning fields, cost/timing, replay, and subagent findings in the design's provider profile table.
- [ ] 1.2 Qualify the running Kimi version's structured stdout and wire formats; deliver sanitized fixtures plus a supported mapping or explicit unavailable-format result, and verify scope/additivity is established from evidence rather than event labels.
- [ ] 1.3 Implement strict usage observation, source binding, metric/provenance, final record, capability, page, and internal finalization models in `usage_models.py`; add model tests covering missing versus reported zero, derived provenance, overlapping counters, managed/native-observed identities, source redaction, and session-only capability.
- [ ] 1.4 Document the record contract and provider qualification matrix in `docs/reference/run-phase/usage-records.md`; verify every claimed mapping has a fixture/version reference or an explicit unknown/unavailable result, and confirm fixtures contain no credentials, private prompts, or response bodies.

## 2. Shared Ledger and Resumable Cursors

- [ ] 2.1 Implement the independent current-schema runtime-session ledger in `usage_store.py`, including bindings, observations, checkpoints, pending turns, immutable final records, and a unique stream incarnation; add store tests for schema creation, unique identities, equivalent replay, conflicting duplicates, and isolation from gateway queue storage.
- [ ] 2.2 Add transactional observation/checkpoint commits and pending-turn/final-record commits with competing-writer checkpoint validation; verify crash injection and concurrent-writer tests cannot advance beyond uncommitted evidence, lose accepted batches, or produce duplicate final rows.
- [ ] 2.3 Implement bounded finalization-order paging with default 100 and maximum 500 records; verify non-null end cursors for queryable streams, initial empty-stream position zero, empty-page polling, late finalization, replay no-ops, wrong-stream/future-position rejection, store replacement, and restart continuity.
- [ ] 2.4 Document ledger ownership, staging, schema failures, immutable records, and cursor polling in the system-files and usage references; verify the polling example retains its cursor when `has_more` is false and after an empty page.

## 3. Provider Adapters and Turn Assembly

- [ ] 3.1 Implement the Codex adapter using qualified request records and version-specific fallback profiles; verify native response-ID deduplication, provider turn membership, cumulative exec completion handling, repeated `token_count` snapshots, cache/reasoning overlap, compaction, and parent-history replay against fixtures.
- [ ] 3.2 Implement the Claude adapter with validated summary scope and message/request rules; verify repeated content-block snapshots, copied sessions, parent/sidechain replay, cache-read/write counters, model-specific accounting, and partial-response evidence remain distinct where required and contribute once.
- [ ] 3.3 Implement qualified Kimi parsing and capability selection, preserving unsupported-version behavior; verify legacy and newer wire fixtures distinguish request increments from summaries, do not blindly add turn/session records, and leave absent usage unavailable.
- [ ] 3.4 Implement source selection and turn assembly in `usage_extraction.py`; verify the same request in stdout/logs counts once, a summary is not added to its constituent requests, verified cumulative totals 1000 then 1600 yield turn increments 1000 and 600, and missing/reset/incomparable baselines never create fabricated charges or zeroes.
- [ ] 3.5 Extend assembly tests for per-metric provenance, validated total derivation, unknown overlap, conflicting source variants, accounting-only redaction, and parent-linked subagent breakdowns; update the usage reference with fixture-backed examples and verify parent summaries do not add included child usage again.

## 4. Bound Native-Log Collection

- [ ] 4.1 Implement source resolution and persisted launch/attachment bindings in `usage_collection.py`; verify exact provider-session ownership, provisional new-session binding, shared-home isolation, exclusion of earlier history, and partial coverage when attachment occurs during a turn.
- [ ] 4.2 Implement bounded incremental file ingestion using atomic source checkpoints; verify complete-line progress, partial trailing JSONL, restart replay, truncation, replacement, archived/copied sources, competing collectors, and baseline continuity with deterministic filesystem fixtures.
- [ ] 4.3 Persist collection boundaries and counter epochs across provider resets and relaunches; verify restart does not take a fresh boundary, a new chat does not reuse the old baseline, and preserved older evidence retains its original registry generation.
- [ ] 4.4 Add structured native-turn association using qualified provider markers and existing hook observations; verify managed submissions register before dispatch, delayed hooks/acknowledgements cannot create duplicate charges, managed/native turns merge, direct prompts retain native-observed origin, and steered or ambiguous/session-only evidence cannot fabricate extra turns or metrics.
- [ ] 4.5 Document collection ownership, source qualification, attachment coverage, native turn association, and degraded capability in the usage and session-lifecycle references; verify examples match collector fixtures and no shipped code/test depends on `extern/orphan/`.

## 5. Shared Finalization and Recovery

- [ ] 5.1 Generate unique omitted headless turn IDs before execution, preserve explicit IDs, reject conflicting reuse, and expose resolved IDs in results/completion payloads; update headless/runtime tests and verify failed retries retain separate artifact directories and record identities.
- [ ] 5.2 Persist headless start snapshots and terminal sidecars with original identity, timing, interruption facts, source positions, and evidence cutoff; verify a later relaunch and recovery produce the same final content rather than applying the current generation or clock.
- [ ] 5.3 Integrate source collection, final evidence drain, assembly, and ledger finalization into shared headless execution; verify completed, failed, interrupted, launch-failure, missing-metric, and partial-evidence outcomes across ordinary runtime and CLI paths without changing canonical rendering.
- [ ] 5.4 Finalize qualified native-observed turns from durable terminal evidence; verify active turns and controller timeouts stay pending, actual terminal outcomes retain available metrics, and late evidence beyond the cutoff produces an explicit conflict without mutating history.
- [ ] 5.5 Implement shared reconciliation for pending native ingestion and missed headless/native finalization; verify startup and recorder-outage recovery insert each missing record once, preserve original terminal facts/cutoffs, and coordinate overlapping gateway/passive recovery without terminal locks.
- [ ] 5.6 Update session-lifecycle, system-files, and usage documentation for generated IDs, sidecars, pending turns, source cutoffs, partial records, and recovery; verify documented failed/interrupted/restarted examples match finalization fixtures.

## 6. Gateway Collection Lifecycle and Usage API

- [ ] 6.1 Start/resume qualified bound collection at gateway attachment/startup and release workers on shutdown; add lifecycle tests for replacement instances, source failures, initial attachment boundaries, collector progress, and continued access to already finalized history.
- [ ] 6.2 Add typed `GatewayServiceRuntime.get_usage()`, `GET /v1/usage`, and `GatewayClient.get_usage()`; verify headless and qualified TUI pages, session-only/unqualified/degraded capabilities, resumable empty/end pages, bounded limits, HTTP 422 validation, safe HTTP 503 storage errors, and active-turn reads without execution locks or synchronous source scans.
- [ ] 6.3 Document gateway source capability, collection health, cursor polling, storage errors, and finalized-only behavior in gateway contracts/index and the usage reference; verify request/response examples match typed client tests.

## 7. Passive-Server Usage and Gateway Projection

- [ ] 7.1 Implement server-managed usage queries and shared finalization/recovery integration against the authority manifest's ledger; verify existing managed turn IDs, overlapping stdout/log evidence, resumed cumulative accounting, partial interruption metrics, recorder outages, and history reads without a live controller.
- [ ] 7.2 Implement gateway-backed usage projection with server-managed precedence; verify qualified TUI records, capability/health and cursor preservation, no second file collector/history, 404 unknown agents, 409 ambiguity, 502 connectivity failures, and upstream 422/503 errors.
- [ ] 7.3 Document maintained usage queries, source precedence, TUI capabilities, and external-controller polling in `docs/reference/managed_agent_api.md`; verify the example counts stable record IDs once and retains its cursor after an empty page.

## 8. End-to-End Qualification

- [ ] 8.1 Add integration coverage across CLI, direct gateway, and passive-server headless paths for success, failure, interruption, late finalization, provider reset, relaunch, and recorder recovery; verify stable IDs, original outcomes/timing, correct source selection, partial metrics, and cursor continuity.
- [ ] 8.2 Add unattended TUI collection integration coverage for qualified Claude/Codex profiles, direct and managed prompts, mid-conversation attachment, fork/subagent replay, source rotation, and gateway restart; verify no pre-attachment or duplicate charges and explicit limitations where association is unsupported.
- [ ] 8.3 Run live headless and unattended TUI qualification using `houmao-mgr`/`houmao-passive-server`, with Claude `tests/fixtures/auth-bundles/claude/kimi-coding/` and Codex `tests/fixtures/auth-bundles/codex/yunwu-openai/` by default; verify public records against sanitized exact-version evidence and keep disposable artifacts under `tmp/usage-qualification/`.
- [ ] 8.4 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, and targeted usage integration suites; verify all pass, then run strict OpenSpec validation and confirm the delivered documentation/provider matrix matches the qualified behavior.
