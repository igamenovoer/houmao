## Context

`gig_agents.agents.brain_launch_runtime` currently uses plain dataclasses plus `dict[str, Any]` payloads across several boundaries:

- Persisted runtime artifacts (`launch_plan` payload and `session_manifest`) are built as dicts and validated via a lightweight, custom JSON Schema validator.
- Runtime orchestration (`runtime.py`) performs resume-time validation using repeated `isinstance(...)` checks and ad-hoc field extraction.
- CAO integration uses a shared `gig_agents.cao.rest_client.CaoRestClient` that currently sends JSON request bodies and uses parameter names that do not match the vendored CAO server’s documented/implemented API contract.

The repo vendors a CAO server implementation under `extern/orphan/cli-agent-orchestrator/` with FastAPI + Pydantic models, and its API contract differs from the current client/backend assumptions (query params like `provider`, `agent_profile`, `message`, and response shapes like `Terminal` and `TerminalOutputResponse`).

Separately, the CAO backend must apply allowlisted credential env vars at launch time. The vendored CAO API does not provide an env parameter on session/terminal creation, so env propagation must be handled via tmux session environment (or explicitly rejected when not possible).

## Goals / Non-Goals

**Goals:**

- Add Pydantic-validated models at boundaries where data crosses modules or processes:
  - persisted runtime artifacts (session manifest + launch-plan payload),
  - CAO REST request/response payloads.
- Keep internal runtime models as plain dataclasses when internal-only (per user preference), and convert to/from Pydantic models only at the persistence + HTTP boundaries.
- Fix the CAO REST client and CAO backend to match the vendored CAO server API contract (parameter names, parameter locations, and response shapes).
- Provide clear, actionable validation errors (field path + reason) for invalid manifests and invalid CAO responses.
- Keep Python typing as tight as practical:
  - minimize `Any` and untyped `dict[str, Any]` at boundaries,
  - prefer typed models/aliases (`Literal`/`Enum`, `Annotated` IDs, `Protocol`) and explicit narrowing helpers,
  - keep `mypy src` green without pervasive `# type: ignore` in core paths.
- Provide live demo scripts (manual E2E, not unit tests) under `scripts/demo/<purpose-slug>/...` that actually run prompts against real cloud providers using local credentials under `agents/brains/api-creds/`.

**Non-Goals:**

- Rewriting the entire runtime to use `pydantic.BaseModel` for all internal types.
- Changing user-facing CLI surface semantics (beyond bug fixes and improved error reporting).
- Implementing new CAO server features; this change is client/runtime-side only.

## Decisions

### 1) Use Pydantic for boundary models; keep internal-only dataclasses

**Decision:** Introduce Pydantic `BaseModel` types for:

- persisted artifact payloads (`launch_plan` payload v1 and `session_manifest` v1),
- CAO REST request/response shapes (health, terminal, output, inbox, etc.).

Keep internal execution-time types as plain dataclasses when they are not persisted or transmitted as whole objects.

**Rationale:** This yields strong validation and typed payloads where drift is costly, while minimizing churn and preserving simple internal logic structures.

**Alternatives considered:**

- Convert all runtime models to `BaseModel` (larger refactor; higher churn).
- Use Pydantic dataclasses everywhere (still couples internal logic to Pydantic semantics).
- Keep current dict+schema approach (does not address CAO contract mismatch; weaker typing at module boundaries).

### 2) Tight typing policy: minimize `Any` and maximize explicit narrowing

**Decision:** For this refactor, we will treat `Any` as a last resort. New/refactored code SHOULD prefer:

- Typed Pydantic models for persisted artifacts and CAO HTTP payloads.
- Narrow Python types for internal surfaces:
  - `InteractiveSession` `Protocol` (or explicit unions) instead of `Any` controller/session fields.
  - `Literal`/`Enum` discriminators (backend kind, provider type, terminal status).
  - `Annotated`/`NewType` identifiers where it improves safety (for example terminal IDs).
- For “unknown JSON” that must remain flexible (for example tool-specific event payloads), use a `JsonValue`/`JsonObject` style alias (recursive union) instead of `Any`, and narrow with `isinstance(...)` checks at use sites.
- For repository-loaded YAML/JSON manifests, type them as `Mapping[str, object]` (or a similar non-`Any` shape) and use dedicated `require_*` helper functions to narrow to `str`, `list[str]`, and `Mapping[...]` as needed.

**Rationale:** Tight types reduce drift and make refactors safer. Pydantic models provide strong boundary validation; explicit narrowing helpers keep dynamic data safe without infecting the codebase with `Any`.

**Alternatives considered:**

- Keep `Any` for convenience (faster to write but undermines mypy and makes boundary drift harder to catch).
- Over-model every possible tool payload shape (high effort, brittle, and not necessary for this change).

### 3) Persisted artifact contract: strict Pydantic models aligned to existing v1 JSON Schemas

**Decision:** Implement strict Pydantic models for the v1 persisted artifacts (forbid unknown fields), aligned with the existing checked-in JSON Schema assets (`*.v1.schema.json`). Validation on write/read will be performed via Pydantic, with optional schema consistency checks in tests/tooling to prevent drift between model and packaged schema files.

**Rationale:** Pydantic provides better error reporting and easier evolution, while keeping the existing schema assets as versioned documentation and a cross-language contract.

**Alternatives considered:**

- Keep using the custom JSON Schema validator as the only gate (less ergonomic; duplicates parsing/validation logic).
- Add a full JSON Schema validation library dependency (more dependencies than needed if Pydantic already exists).

### 4) CAO REST client contract: match vendored CAO server (query params + typed responses)

**Decision:** Refactor `gig_agents.cao.rest_client` to:

- encode request parameters as query parameters with CAO’s names (`provider`, `agent_profile`, `message`, etc.),
- parse CAO JSON responses into typed Pydantic models (e.g., `Terminal`, `TerminalOutputResponse`) rather than probing for multiple key variants,
- treat CAO error responses (`{"detail": ...}`) as structured errors surfaced to callers.

**Rationale:** The CAO server is vendored in-repo and already defines the canonical response shapes; matching it reduces runtime brittleness and enables reuse by other runtimes.

**Alternatives considered:**

- Continue “best-effort” key probing (tolerant but hides contract mismatches and increases debugging time).
- Treat CAO payloads as untyped dicts (no guardrails against drift).

### 5) CAO allowlisted env propagation: own the tmux session

**Decision:** For CAO-backed sessions, apply allowlisted env vars via tmux session environment:

- Create a unique tmux session name per runtime session.
- Set environment variables on that tmux session (home selector env var + allowlisted credential env vars).
- Spawn the CAO terminal into that existing tmux session via `POST /sessions/{session_name}/terminals`.

If tmux is unavailable, fail fast with an explicit error (rather than silently launching with missing credentials).

**Rationale:** The CAO API does not support a per-terminal env payload; tmux environment inheritance is the reliable mechanism to satisfy the runtime’s credential allowlist requirement.

**Alternatives considered:**

- Pass env in CAO REST calls (not supported by the vendored CAO server).
- Encode env into agent profile (not supported and risks secret leakage into profile files).
- Launch without env injection (breaks credential contract; hard-to-debug auth failures).

### 6) CAO provider mapping is explicit and validated

**Decision:** Map runtime tool identities to CAO provider values and validate support:

- `codex` → `codex`
- `claude` → `claude_code`
- `gemini` → not supported by vendored CAO providers (error with clear message unless an override is provided)

**Rationale:** CAO provider identifiers are an external contract; explicit mapping avoids implicit mismatches and makes unsupported combinations fail clearly.

### 7) Live demo scripts are first-class deliverables (real providers, not mocks)

**Decision:** In addition to smoke/unit tests, ship opt-in demo scripts under `scripts/demo/<purpose-slug>/...` that:

- launch CAO-backed sessions for providers CAO supports (`codex`, `claude_code`) and successfully process at least one prompt end-to-end,
- launch a non-CAO Gemini headless session and successfully process at least one prompt end-to-end (since the vendored CAO provider set does not include Gemini),
- use local credential profiles under `agents/brains/api-creds/<tool>/<cred-profile>/...`,
- follow the “Tutorial Pack” pattern described in `context/instructions/explain/make-api-tutorial-pack.md`:
  - one directory per purpose under `scripts/demo/<purpose-slug>/`,
  - a step-by-step `README.md` (goal, prerequisites, run instructions, verify instructions, troubleshooting, appendix),
  - a single `run_demo.sh` entrypoint that uses a temporary workspace under `tmp/` (non-destructive),
  - tracked minimal `inputs/` for any required non-secret files,
  - a tracked `expected_report/` snapshot plus a sanitizer script (or an explicit invariant-based verifier) so developers can re-run and confirm the demo produced a valid outcome even if model text is not fully deterministic,
- SKIP an individual demo (print a clear skip reason and exit 0 for that demo) when:
  - credentials are missing,
  - credentials are invalid/unauthorized, or
  - connectivity is unavailable/lost (CAO server unreachable, network errors, timeouts to cloud providers),
- fail with clear, actionable errors for non-skip failures (for example invalid CLI arguments, missing required binaries, or unexpected response parsing/validation errors),
- avoid printing secret values (log env var names and high-level progress only).

These demos are intended for developers to run manually; they are not expected to run in CI.

**Rationale:** The CAO boundary has historically drifted; an end-to-end, live-provider demo is the quickest way to validate that the runtime actually launches, sends prompts, and receives real output.

## Risks / Trade-offs

- **Stricter validation may reject previously-accepted junk** → Mitigation: keep error messages actionable (field path + expected/actual), and keep schemas versioned so behavior is predictable.
- **CAO server schema drift across versions** → Mitigation: parse responses with `extra="ignore"` for responses where CAO may add fields, while requiring core fields (`id`, `status`, etc.) and surfacing CAO `detail` errors clearly.
- **tmux dependency for CAO env propagation** → Mitigation: fail fast with a clear message and document the requirement; optionally add a “no-env” debug mode later (out of scope here).
- **Tighter typing may increase boilerplate and refactor churn** → Mitigation: keep “dynamic” zones isolated (single JSON alias + require/narrow helpers) and focus strict typing at persistence/HTTP boundaries where it pays for itself.
- **Live demos require real credentials and may incur cost / rate limits** → Mitigation: keep prompts minimal, document prerequisites clearly, and ensure scripts are opt-in and do not run by default in test workflows.
- **Risk of secret leakage via demo logs** → Mitigation: never echo `vars.env` contents; log only env var names and redact any values in printed diagnostics.
