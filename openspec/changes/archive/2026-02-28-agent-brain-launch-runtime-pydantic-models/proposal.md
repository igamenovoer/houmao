## Why

The brain launch runtime currently relies on `dataclasses` plus ad-hoc `dict[str, Any]` payloads at module boundaries (persisted manifests, CAO REST responses, CLI JSON). This makes it easy for payload shapes to drift, produces weaker validation errors, and complicates safe refactors.

Separately, the repo’s CAO REST integration does not currently match the vendored CAO server’s documented/implemented API contract (query parameters and field names), which makes the CAO backend unreliable/non-functional and blocks reuse by `agent-team-orchestration-runtime`.

## What Changes

- Introduce Pydantic models for boundary data that crosses modules and processes:
  - persisted runtime artifacts (session manifest and launch-plan payloads),
  - CAO REST request/response payloads (health, sessions/terminals, input/output, inbox).
- Keep internal runtime types as plain dataclasses when they are internal-only; convert to/from Pydantic models at the persistence and HTTP boundaries.
- Fix the CAO REST client + CAO backend to conform to the vendored CAO server contract:
  - correct parameter names (`provider`, `agent_profile`, `message`) and encoding (query parameters),
  - parse responses into typed models instead of best-effort key probing.
- Address CAO environment propagation for allowlisted credential env vars:
  - implement a tmux-session-owned strategy (set tmux session env vars before spawning terminals), and/or
  - explicitly document constraints and provide best-effort fallbacks when tmux is unavailable.
- Add live demo scripts under `scripts/demo/<purpose-slug>/...` that exercise real end-to-end prompt processing against cloud providers (not mocks), using local credential profiles under `agents/brains/api-creds/`.
- Update unit tests and docs to reflect the new typed boundaries and CAO contract.

## Capabilities

### New Capabilities

- `brain-launch-runtime-pydantic-boundaries`: Define and enforce Pydantic-validated models for persisted runtime artifacts and cross-module payloads (while keeping internal-only models as dataclasses).
- `cao-rest-client-contract`: Define a typed CAO REST boundary that matches the vendored CAO server’s API contract and enables reliable CAO-backed sessions.

### Modified Capabilities

<!-- None (this is primarily a correctness + refactor change; existing specs do not yet cover this runtime). -->

## Impact

- Affected code:
  - `src/agent_system_dissect/agents/brain_launch_runtime/**` (manifest I/O, resume logic, CLI JSON output)
  - `src/agent_system_dissect/cao/**` (shared CAO REST client and models)
- Affected tests:
  - `tests/unit/agents/brain_launch_runtime/**`
- Affected docs:
  - `docs/reference/brain_launch_runtime.md`
- Affected demo scripts:
  - `scripts/demo/**`
- Dependencies:
  - Uses `pydantic` (already a project dependency).
