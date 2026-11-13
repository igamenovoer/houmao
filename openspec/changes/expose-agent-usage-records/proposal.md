# Proposal

## Why

External budget controllers need reliable per-turn usage across headless and TUI agents without parsing private logs themselves. GitHub issue #83 needs this contract before DSH and Pi are added; existing headless payloads and native session logs provide evidence, but their request, turn, and cumulative counters require different accounting rules.

## What Changes

- Add provider-specific accounting adapters for preserved structured headless output and native session logs, independent of execution mode. Qualify Claude and Codex first; enable Kimi mappings only against captured evidence from the running provider version.
- Bind collection to the managed agent's provider home and session identity. Persist launch or attachment boundaries so resumed history is not charged again, and checkpoint incremental native-log ingestion for restart recovery.
- Introduce internal accounting observations with provider request/turn identities, source profiles, scopes, and provenance. Deduplicate repeated responses, copied fork/subagent history, and overlapping stdout/log evidence before assembling final records.
- Prefer verified turn summaries or distinct request measurements according to each provider profile. Derive cumulative deltas only with a comparable baseline from the same provider session and counter epoch; preserve unknowns when attribution or continuity is uncertain.
- Add versioned normalized records with stable agent, runtime-session, generation, accounting-turn, and provider identities. Distinguish managed turns from directly observed native turns, missing metrics from reported zero, and token totals from overlapping cache/reasoning breakdowns.
- Record completed, failed, and interrupted headless turns through the shared execution path. Record TUI turns only when structured evidence establishes turn identity and final outcome; use existing hooks for association where available.
- Add one per-runtime-session SQLite ledger for staged observations, source checkpoints, pending turns, and immutable finalized records. Reconciliation recovers interrupted collection and missed finalization without producing duplicate charges.
- **BREAKING:** Headless prompts without caller-supplied turn/artifact IDs shall receive unique generated IDs and artifact directory names instead of index-only names. Explicit submission IDs remain unchanged.
- Add direct gateway `GET /v1/usage` and passive-server `GET /houmao/agents/{agent_ref}/usage` queries with bounded finalization-order pages. A queryable stream always returns a resumable cursor, including at its current end.
- Report capability from validated evidence and turn association rather than backend name. TUI agents with supported native logs can expose finalized usage; session-only evidence does not imply per-turn accounting.
- Add sanitized provider fixtures, deduplication and cumulative-scope regression coverage, native-log recovery tests, managed-path integration tests, and documentation of accounting limits.

This change excludes budget policy, price estimation, active-turn public streaming, arbitrary user-home scans, and mandatory historical backfill. It uses ccusage as a source reference; shipped Houmao code and tests must remain independent of the ignored checkout.

## Capabilities

### New Capabilities

- `agent-usage-records`: Provider-faithful usage collection, source binding, scope normalization, deduplication, turn association, immutable finalized records, recovery, and bounded incremental retrieval.

### Modified Capabilities

- `agent-gateway`: Add usage collection lifecycle and a read-only query for headless and qualified TUI agents, with evidence-based capability responses and no terminal-mutation lock acquisition.
- `passive-server-headless-management`: Finalize server-managed headless accounting through the shared ledger and query durable history without a live controller.
- `passive-server-gateway-proxy`: Preserve authoritative source selection, usage capabilities, cursors, and errors when projecting gateway-attached agent accounting.

## Impact

- **Runtime:** new accounting models, provider adapters, collection, extraction, persistence, and recovery under `src/houmao/agents/realm_controller/`; shared headless lifecycle instrumentation and consumption of existing hook observations for qualified TUI collection.
- **Gateway and passive server:** collection startup/recovery, typed usage pages and clients, the two read routes, and existing managed-agent resolution.
- **Storage:** an independent runtime-session usage database and durable headless start/finalization evidence; existing gateway queue storage stays separate.
- **Dependencies:** standard-library SQLite and file I/O. No new third-party runtime dependency or runtime import from `extern/`.
- **Tests and docs:** sanitized fixtures for exact provider versions, hermetic adapter/collector/store/API tests, managed and TUI integration coverage, and run-phase, system-files, gateway, and managed-agent references.
