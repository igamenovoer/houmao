## 1. Runtime Recovery And Error Isolation

- [x] 1.1 Broaden tmux-backed name-resolution logic so missing, blank, or stale `AGENTSYS_MANIFEST_PATH` and `AGENTSYS_AGENT_DEF_DIR` can fall back to fresh shared-registry metadata while manifest or identity mismatches still fail fast
- [x] 1.2 Update manifest-persisting runtime control flows so post-success shared-registry refresh failures are surfaced as warnings or diagnostics instead of replacing successful prompt, control-input, interrupt, mailbox-refresh, or close outcomes
- [x] 1.3 Update authoritative `stop-session` teardown so a successful backend termination still returns success when later shared-registry cleanup fails, while preserving operator-visible cleanup failure reporting

## 2. Registry Contract And Storage Hardening

- [x] 2.1 Tighten `LiveAgentRegistryRecordV1` timestamp validation to require timezone-aware `published_at` and `lease_expires_at` values and reject naive timestamps
- [x] 2.2 Change shared-registry lookup paths to treat malformed, schema-invalid, or expired records as unusable or stale resolution results instead of lookup-stopping errors
- [x] 2.3 Harden shared-registry atomic-write helpers to remove temp files when the final replace step fails
- [x] 2.4 Extend stale-registry cleanup so it continues past per-directory removal failures and reports failed removals separately from preserved live directories

## 3. Verification And Documentation

- [x] 3.1 Add unit and integration coverage for tmux-pointer fallback, malformed-record lookup behavior, timezone-aware timestamp enforcement, refresh-failure isolation, stop cleanup isolation, temp-file cleanup, and partial cleanup-failure reporting
- [x] 3.2 Update registry and realm-controller docs to describe the refined fallback semantics, timezone-aware lease contract, and cleanup failure reporting expectations
