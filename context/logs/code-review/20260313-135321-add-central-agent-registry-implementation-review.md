# Code Review: add-central-agent-registry implementation

## Scope

- Change artifacts reviewed:
  - `openspec/changes/add-central-agent-registry/proposal.md`
  - `openspec/changes/add-central-agent-registry/design.md`
  - `openspec/changes/add-central-agent-registry/specs/agent-discovery-registry/spec.md`
  - `openspec/changes/add-central-agent-registry/specs/brain-launch-runtime/spec.md`
  - `openspec/changes/add-central-agent-registry/tasks.md`
- Implementation reviewed:
  - `src/houmao/agents/realm_controller/registry_models.py`
  - `src/houmao/agents/realm_controller/registry_storage.py`
  - `src/houmao/agents/realm_controller/runtime.py`
  - `src/houmao/agents/realm_controller/cli.py`
  - related manifest/schema/docs/tests touched by `feat: add central agent registry`

## Findings

### 1. High: shared-registry fallback only happens when the tmux session is missing, not when tmux-local discovery is unavailable

- Spec / docs intent:
  - `openspec/changes/add-central-agent-registry/proposal.md:13` says runtime resolution should use the shared registry when "tmux-local discovery" is unavailable.
  - `docs/reference/realm_controller.md:59` says runtime falls back "when name-based control cannot resolve a local tmux session".
- Current implementation:
  - `src/houmao/agents/realm_controller/runtime.py:647-660` only enters the registry fallback path when `_ensure_tmux_session_exists()` raises.
  - If the tmux session exists but `AGENTSYS_MANIFEST_PATH` is missing/stale, `_resolve_manifest_path_from_tmux_session()` raises directly at `src/houmao/agents/realm_controller/runtime.py:662` and `src/houmao/agents/realm_controller/runtime.py:1156-1177`.
  - The same applies when the local tmux-published `AGENTSYS_AGENT_DEF_DIR` is missing/stale in `src/houmao/agents/realm_controller/runtime.py:667-674` and `src/houmao/agents/realm_controller/runtime.py:1220-1254`.
- Why this matters:
  - A healthy session with a fresh shared-registry record can still become uncontrollable if the local tmux env pointers are lost or corrupted.
  - That is exactly the class of cross-root recovery scenario the change is trying to improve.
- Reproduction:
  - I verified this with a small `pixi run python` snippet: when `tmux has-session` succeeds but `show-environment` returns `unknown variable: AGENTSYS_MANIFEST_PATH`, `resolve_agent_identity()` fails with `Manifest pointer missing...` instead of consulting the registry.
- Suggested fix:
  - Treat the whole tmux-local name-resolution path as fallback-eligible, not just the `has-session` check.
  - Fall back to `_resolve_agent_identity_from_shared_registry()` for discovery failures such as missing/stale `AGENTSYS_MANIFEST_PATH` or `AGENTSYS_AGENT_DEF_DIR`, while still surfacing hard validation mismatches when both local and registry sources are unusable.
  - Add tests for:
    - tmux session exists but `AGENTSYS_MANIFEST_PATH` is missing, registry fresh
    - tmux session exists but `AGENTSYS_AGENT_DEF_DIR` is stale, registry fresh

> **DECISION: Accept with refinement — treat missing or stale tmux-local discovery pointers as shared-registry fallback cases, but keep hard identity mismatches as direct failures.**
> Rationale: The proposal and docs both frame the registry as the recovery path when tmux-local discovery is unavailable, and a session with missing `AGENTSYS_MANIFEST_PATH` or stale `AGENTSYS_AGENT_DEF_DIR` fits that category. We should broaden fallback beyond `tmux has-session` failure, but not hide manifest/session-name mismatches or other hard validation problems that indicate a deeper ownership error.

### 2. Medium: malformed registry records raise hard errors instead of producing the spec’s not-found/stale result

- Spec intent:
  - `openspec/changes/add-central-agent-registry/specs/agent-discovery-registry/spec.md:145-149` says missing, malformed, or non-fresh records should yield an explicit not-found or stale-record result.
- Current implementation:
  - `src/houmao/agents/realm_controller/registry_storage.py:96-99` calls `_read_live_agent_record()` whenever the file exists.
  - `_read_live_agent_record()` raises `SessionManifestError` for invalid JSON or schema failures at `src/houmao/agents/realm_controller/registry_storage.py:307-325`.
  - `resolve_live_agent_record()` does not catch those exceptions at `src/houmao/agents/realm_controller/registry_storage.py:102-118`.
  - `src/houmao/agents/realm_controller/runtime.py:1188-1217` therefore fails hard during registry fallback instead of treating the record as unusable and moving on.
- Why this matters:
  - One corrupted `record.json` blocks resolution for that agent until manual cleanup, even though the contract describes malformed records as a stale/not-found condition.
  - This also makes the runtime more brittle than the cleanup tool contract implies.
- Reproduction:
  - I verified this with a small `pixi run python` snippet: a malformed `record.json` causes `resolve_live_agent_record("gpu")` to raise `SessionManifestError: Invalid JSON in registry record ...` rather than returning `None`.
- Suggested fix:
  - Decide on one of these behaviors and make code/tests/spec line up:
    - preferred: `resolve_live_agent_record()` catches read/validation failures and returns `None` (or a structured stale result), leaving cleanup to remove the bad directory later
    - alternative: keep the exception, but then tighten the spec/docs to say malformed records are surfaced as explicit validation errors, not not-found/stale
  - Add a unit test for malformed record resolution behavior so the contract stays pinned.

> **DECISION: Accept the preferred direction — malformed registry records should be treated as unusable/stale for resolution instead of aborting lookup.**
> Rationale: The delta spec already says missing, malformed, or non-fresh records yield a not-found or stale result, and that matches the registry's role as an optional locator layer rather than an authoritative runtime store. Keep strict validation for diagnostics and cleanup helpers, but resolution and fresh-record ownership checks should not require manual repair before the system can move on.

### 3. Medium: the “strict” record validator accepts timezone-less timestamps, which makes freshness depend on the reader’s local timezone

- Current implementation:
  - `src/houmao/agents/realm_controller/registry_models.py:188-193` validates timestamps by calling `_parse_iso8601_timestamp()`.
  - `src/houmao/agents/realm_controller/registry_models.py:243-247` accepts naive ISO timestamps such as `2026-03-13T12:00:00`.
  - Freshness checks later parse those strings with `datetime.fromisoformat(...).astimezone(UTC)` at `src/houmao/agents/realm_controller/registry_storage.py:246-247` and `src/houmao/agents/realm_controller/registry_storage.py:340-343`.
- Why this matters:
  - For naive timestamps, `astimezone(UTC)` interprets them in the local timezone of the reading process.
  - The same on-disk record can therefore expire at different UTC instants on different machines or shells.
  - That weakens the “strict versioned schema” goal of the registry contract.
- Reproduction:
  - The model currently accepts a record whose `published_at` is `2026-03-13T12:00:00` with no offset.
  - I also verified with `TZ=America/New_York pixi run python` that the same naive timestamp is interpreted as `2026-03-13T16:00:00+00:00`, proving freshness depends on local timezone settings.
- Suggested fix:
  - Require timezone-aware timestamps in `LiveAgentRegistryRecordV1` validation and reject naive values.
  - Alternatively, normalize naive timestamps to UTC during validation, but that is usually a weaker contract than requiring offsets explicitly.
  - Add a unit test that rejects naive timestamps and a test that accepts `Z` / `+00:00` values.

> **DECISION: Accept — require timezone-aware timestamps in the v1 record schema and reject naive values.**
> Rationale: This record format is meant to be a strict shared contract, and freshness must not depend on the reader's local timezone. The current publisher already emits aware UTC timestamps, so tightening validation removes ambiguity without weakening an intended compatibility promise.

### 4. Medium: registry refresh failures propagate into primary operations, making the secondary discovery layer break primary control flows

- Design intent:
  - `openspec/changes/add-central-agent-registry/design.md` establishes the registry as a "locator layer" that "coexists with existing tmux session environment discovery pointers" — a secondary, additive discovery surface.
  - The spec says the registry SHALL NOT replace existing discovery mechanisms.
- Current implementation:
  - `src/houmao/agents/realm_controller/runtime.py:322-337`: `persist_manifest()` calls `self.refresh_shared_registry_record()` by default, which calls `publish_live_agent_record()`.
  - `publish_live_agent_record()` at `src/houmao/agents/realm_controller/registry_storage.py:121-155` can raise `SessionManifestError` for: expired lease, ownership conflict, write failure, or post-publish verification failure.
  - These exceptions propagate unhandled through `persist_manifest()` and into every caller: `send_prompt()` (line 207), `interrupt()` (line 214), `close()` (line 280), `send_input_ex()` (line 241/252), and `refresh_mailbox_bindings()` (line 319).
- Why this matters:
  - A transient registry issue (disk full on `~/.houmao`, NFS hiccup, unexpected ownership conflict from a stale record) can fail a `send_prompt` or `interrupt` call even though the tmux session and manifest are perfectly healthy.
  - The registry is supposed to be an optional discovery accelerator, not a mandatory gate on every runtime action.
- Suggested fix:
  - Wrap the `refresh_shared_registry_record()` call inside `persist_manifest()` with a try/except that logs or captures the error as a warning rather than propagating it.
  - Alternatively, make the `refresh_registry` parameter default-false and let callers opt in at well-defined lifecycle boundaries (start, resume, gateway attach/detach, stop) rather than on every manifest persist.

> **DECISION: Accept with refinement — registry refresh must not overturn an already-successful primary runtime action, but publication should stay enabled on the existing lifecycle hooks.**
> Rationale: Tasks 2.1-2.3 intentionally tie registry refresh to manifest-persisting and lifecycle-owned publication points, so we should not back away from those hooks. The fix is to isolate refresh failures on post-action paths such as prompt/control/mailbox flows and surface them as warnings or diagnostics, while still allowing explicit start/resume-time publication failures to remain visible to operators.

### 5. Medium: `stop()` does not isolate registry cleanup errors from the stop result

- Current implementation:
  - `src/houmao/agents/realm_controller/runtime.py:268-274`: after successful `backend_session.terminate()`, `stop()` calls `self.clear_shared_registry_record()`.
  - `clear_shared_registry_record()` at line 452-461 calls `remove_live_agent_record()`.
  - `remove_live_agent_record()` at `src/houmao/agents/realm_controller/registry_storage.py:158-185` uses `shutil.rmtree(record_dir, ignore_errors=False)`, which raises on permission errors or filesystem issues.
  - An `rmtree` failure from registry cleanup would propagate out of `stop()`, even though the backend was already terminated successfully.
- Why this matters:
  - The operator sees a failed stop even though the session was successfully killed. A registry directory permission issue (e.g., shared NFS mount, container filesystem quirk) should not prevent returning a successful stop result to the caller.
- Suggested fix:
  - Wrap `self.clear_shared_registry_record()` in `stop()` with a try/except that records the error but still returns the successful `SessionControlResult` from `terminate()`.
  - Consider also using `ignore_errors=True` in `remove_live_agent_record` since the cleanup entrypoint exists precisely to clean up leftovers.

> **DECISION: Accept the stop-path isolation, reject silent `ignore_errors=True` cleanup.**
> Rationale: Once backend termination succeeds, `stop()` should report that success even if registry cleanup hits a filesystem problem, because the registry is secondary metadata. We should still preserve cleanup failure information for operators instead of discarding it silently inside `remove_live_agent_record()`.

### 6. Low: `_write_json_atomically` does not clean up the temp file when the atomic rename fails

- Current implementation:
  - `src/houmao/agents/realm_controller/registry_storage.py:328-337`:
    ```python
    temp_path.write_text(...)
    temp_path.replace(path)
    ```
  - If `temp_path.write_text()` succeeds but `temp_path.replace(path)` fails (cross-filesystem move, permission, disk full on metadata update), the temp file `.record.json.<pid>.<uuid>.tmp` is left behind.
- Why this matters:
  - Over time, failed publishes can accumulate orphaned temp files in `live_agents/<key>/` directories. The cleanup entrypoint only looks for `record.json` presence — it does not remove stale `.tmp` files.
- Suggested fix:
  - Add a `try/except/finally` to remove the temp file on failure:
    ```python
    try:
        temp_path.replace(path)
    except OSError:
        temp_path.unlink(missing_ok=True)
        raise
    ```

> **DECISION: Accept — clean up orphaned temp files when atomic replace fails.**
> Rationale: The specific cross-filesystem example is not applicable here because the temp file is written in the target directory, but `replace()` can still fail for permission or filesystem-state reasons. Cleaning up the temp file is small, local hardening with no contract downside.

### 7. Low: `cleanup_stale_live_agent_records` aborts on the first unremovable directory

- Current implementation:
  - `src/houmao/agents/realm_controller/registry_storage.py:225-226`: cleanup calls `shutil.rmtree(candidate, ignore_errors=False)` for each stale directory.
  - If any single directory fails to remove (busy file handle, permission issue), the entire cleanup function raises and no further directories are processed.
- Why this matters:
  - In a registry with many stale entries, a single problematic directory prevents cleanup of all subsequent entries, requiring the operator to manually intervene or re-run cleanup after fixing the one directory.
- Suggested fix:
  - Catch per-directory `OSError` and continue processing remaining directories, collecting failures into the result or logging them:
    ```python
    try:
        shutil.rmtree(candidate, ignore_errors=False)
        removed.append(candidate.name)
    except OSError:
        preserved.append(candidate.name)  # or a separate "failed" list
    ```

> **DECISION: Accept with refinement — cleanup should continue past one bad directory and report removal failures explicitly.**
> Rationale: A single permission or busy-file problem should not block all later stale-entry cleanup. The follow-up should extend the cleanup result or CLI reporting so failed removals are distinguishable from genuinely preserved fresh records, rather than collapsing both cases into the same bucket.

### 8. Low: `record_path_for_agent_name` double-canonicalizes through `derive_agent_key`

- Current implementation:
  - `src/houmao/agents/realm_controller/registry_storage.py:82-84`:
    ```python
    canonical_name = canonicalize_registry_agent_name(agent_name)
    key = derive_agent_key(canonical_name)
    ```
  - `derive_agent_key` at `src/houmao/agents/realm_controller/registry_models.py:207-211` internally calls `canonicalize_registry_agent_name(agent_name)` again before hashing.
  - The same pattern appears in `_validate_schema_and_identity()` at line 184 where `derive_agent_key(self.agent_name)` re-canonicalizes an already-validated canonical name.
- Why this matters:
  - Not a correctness bug (canonicalization is idempotent), but it obscures the control flow and makes `derive_agent_key`'s contract ambiguous — callers can't tell whether they should pre-canonicalize or let the function do it.
- Suggested fix:
  - Either make `derive_agent_key` accept only pre-canonicalized input (assert or document that assumption), or remove the upstream canonicalization in callers that already have the canonical form. Consistency in one direction is better than redundant normalization.

> **DECISION: Reject as a required follow-up for this change.**
> Rationale: The duplicate canonicalization is harmless, cheap, and currently serves as a defensive boundary for callers that may pass raw or canonical names. If we later want to simplify it for clarity, that can be a small cleanup-only change, but it does not warrant artifact or implementation churn in this registry rollout.

### 9. Observation: `RegistryMailboxV1.filesystem_root` is a required field but is transport-specific

- Current implementation:
  - `src/houmao/agents/realm_controller/registry_models.py:124-140`: `RegistryMailboxV1` requires `filesystem_root: str` for all transports.
  - `src/houmao/agents/realm_controller/runtime.py:1389`: the builder accesses `mailbox.filesystem_root.resolve()`, which would fail with `AttributeError` if `filesystem_root` is `None` for a non-filesystem transport.
- Why this matters:
  - Currently only `filesystem` transport exists, so this is not a live bug. However, the model's strict required field means adding a non-filesystem mailbox transport would require either a schema version bump or putting a dummy filesystem_root value in the record.
- Suggested fix:
  - Make `filesystem_root` optional (`str | None = None`) so the schema accommodates future transport types without a breaking change. Guard the builder accordingly.

> **DECISION: Reject for v1 — keep `filesystem_root` required while `filesystem` is the only supported mailbox transport.**
> Rationale: The current mailbox contract in this repo only allows `transport="filesystem"`, so requiring `filesystem_root` keeps the schema strict and honest for the only real case we support today. If a non-filesystem transport is introduced later, we can intentionally revise the registry mailbox shape then, rather than weakening the v1 contract preemptively.

## Verification

- Targeted tests run:
  - `pixi run pytest tests/unit/agents/realm_controller/test_registry_storage.py tests/unit/agents/realm_controller/test_runtime_registry.py tests/unit/agents/realm_controller/test_runtime_agent_identity.py tests/unit/agents/realm_controller/test_cli.py tests/integration/agents/realm_controller/test_registry_runtime_contract.py`
- Result:
  - `36 passed in 0.36s`
- Extra manual verification (pass 1):
  - confirmed malformed-record resolution currently raises
  - confirmed tmux-env discovery failure does not fall back to registry
  - confirmed naive timestamps are accepted and interpreted relative to local timezone
- Extra code review verification (pass 2 — findings 4–9):
  - confirmed `persist_manifest()` default-calls `refresh_shared_registry_record()` with no error isolation by tracing runtime.py:322-337 and all call sites
  - confirmed `stop()` at runtime.py:268-274 does not wrap `clear_shared_registry_record()` in try/except
  - confirmed `_write_json_atomically` at registry_storage.py:328-337 has no temp-file cleanup on rename failure
  - confirmed `cleanup_stale_live_agent_records` at registry_storage.py:225-226 uses `ignore_errors=False` with no per-directory catch
  - confirmed `derive_agent_key` re-canonicalizes at registry_models.py:210 and callers pre-canonicalize at registry_storage.py:82-83
  - confirmed `RegistryMailboxV1.filesystem_root` is required (not optional) at registry_models.py:130

## Notes

- No online sources were needed for this review.
- Implementation code was not modified; this report is review-only.
- Findings 1–3 were from the initial review pass. Findings 4–9 were added in a second pass focused on design consistency, error isolation, code structure, and interface cleanliness.
