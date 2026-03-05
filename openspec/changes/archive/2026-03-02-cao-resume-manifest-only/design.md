## Context

`brain_launch_runtime` persists a session manifest for CAO-backed sessions that includes `cao.api_base_url`, `cao.session_name`, and `cao.terminal_id` (and duplicates these fields under `backend_state`). Despite this, resumed operations (`send-prompt`, `stop-session`) still accept `--cao-base-url` and pass it into the resume path, creating a second, potentially conflicting source of truth for the CAO endpoint.

This makes “resume by manifest” unreliable: a caller can provide the correct session manifest but accidentally target a different CAO host (for example via default `http://localhost:9889`), leading to confusing failures or unintended control of the wrong system.

## Goals / Non-Goals

**Goals:**

- Make `--session-manifest` sufficient to address a CAO-backed session for `send-prompt` and `stop-session`.
- Remove the CAO base URL override from resumed operations (CLI and Python API) so there is exactly one authoritative endpoint: `session_manifest.cao.api_base_url`.
- Provide stable, testable error semantics for invalid resume manifests (local validation) vs CAO backend failures (remote/network).
- Keep `start-session` behavior unchanged: creating a CAO-backed session still requires specifying the CAO base URL at creation time, and it is persisted into the manifest.
- Update docs and demos to match the new contract.

**Non-Goals:**

- Provide backwards-compatible flags or shims for the removed CLI options.
- Support “retargeting” an existing session manifest to a different CAO endpoint (reverse proxies, moved servers, etc.).
- Change CAO server semantics or add new CAO REST endpoints.
- Remove `--cao-profile-store` from `send-prompt`/`stop-session` (deferred follow-up; out of scope for this change).

## Decisions

1. **Manifest is the complete address for resumed CAO sessions**
   - For backend `cao_rest`, resumed operations MUST use the manifest’s `cao.api_base_url` and `cao.terminal_id` (and `cao.session_name` for tmux/debug labeling).
   - Any external base URL override is removed to prevent ambiguous targeting.

2. **Remove `--cao-base-url` from `send-prompt` and `stop-session`**
   - The CLI surface is adjusted so users cannot supply a mismatching CAO URL.
   - `--cao-base-url` remains on `start-session` only.

3. **Remove the resume-time CAO URL parameter from the Python API**
   - `resume_runtime_session(...)` no longer accepts an `api_base_url` parameter for CAO resume flows.
   - The resume path reads the CAO URL strictly from the persisted manifest payload.

4. **Fail fast on inconsistent/invalid manifests**
   - If a session manifest indicates `backend=cao_rest` but lacks a valid `cao.api_base_url` (or other required CAO fields), resume fails with an explicit error.
   - Add a defensive invariant check that `cao.api_base_url` matches `backend_state.api_base_url` (they should be identical because both are persisted from the same runtime state).
   - These are treated as *local* validation failures (no CAO network calls should be required to detect them).

5. **Error semantics: local vs remote failures**
   - Local manifest validation failures raise `SessionManifestError` with a message that names the failing field path (for example `cao.api_base_url`, `cao.terminal_id`).
   - CAO network/HTTP failures remain `BackendExecutionError`.

6. **Hermetic unit tests protect the contract**
   - Add unit tests that assert the resumed CAO client/session is constructed using the manifest URL (non-default) and that inconsistent manifests fail fast.
   - Do not add live CAO integration tests to unit CI; keep end-to-end validation in demo packs/manual runs.

## Risks / Trade-offs

- **[Breaking CLI usage]** Existing scripts passing `--cao-base-url` to `send-prompt`/`stop-session` will fail → Mitigation: update in-repo docs/demos and provide clear CLI help text; treat as intentional breaking change.
- **[Less flexibility for proxies]** Users cannot point an existing manifest at a different URL that reaches the same CAO server → Mitigation: require users to start a new session against the desired endpoint (or explicitly edit the manifest if they accept the consequences).
- **[Assumption about manifest validity]** This design assumes session manifests are the authoritative persisted contract → Mitigation: keep strict Pydantic/schema validation on load and add unit tests for CAO resume behavior.
