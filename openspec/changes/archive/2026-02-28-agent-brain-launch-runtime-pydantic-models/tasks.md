## 1. Pydantic Models For Persisted Runtime Artifacts

- [x] 1.1 Define strict Pydantic models for `launch_plan.v1` and `session_manifest.v1` payloads (including per-backend sections)
- [x] 1.2 Update manifest write path to validate via Pydantic before persisting (keep `schema_version=1` and keep secrets out of persisted files)
- [x] 1.3 Update manifest load path to parse/validate via Pydantic and surface field-path errors
- [x] 1.4 Refactor `resume_runtime_session()` to use typed manifest models instead of ad-hoc `isinstance(...)` checks (keep public runtime types as dataclasses)
- [x] 1.5 Add/adjust unit tests for validation failures to assert actionable field-path errors and ensure no secret values are persisted
- [x] 1.6 Add a schema consistency check (test or script) to keep packaged `*.v1.schema.json` aligned with the Pydantic models

## 2. Typed CAO API Models + REST Client Contract Fix

- [x] 2.1 Add Pydantic models for CAO API responses (health, terminal, output, inbox, success/error) matching `extern/orphan/cli-agent-orchestrator`
- [x] 2.2 Refactor `gig_agents.cao.rest_client` to use CAO query parameters and correct field names (`provider`, `agent_profile`, `message`, `mode`) instead of JSON bodies
- [x] 2.3 Update CAO client methods to return typed responses and to surface CAO `detail` errors as structured exceptions
- [x] 2.4 Update unit tests for CAO REST client request/response shapes to match the vendored CAO API contract

## 3. CAO Backend Fixes (Provider Mapping + tmux Env Strategy)

- [x] 3.1 Implement explicit runtime-tool to CAO-provider mapping (`codex`->`codex`, `claude`->`claude_code`) with clear unsupported-tool errors
- [x] 3.2 Implement tmux-session-owned env propagation for CAO backend (create per-session tmux session, set env vars, fail fast if tmux is unavailable)
- [x] 3.3 Update CAO backend launch to spawn terminals via `POST /sessions/{session_name}/terminals` into the pre-created tmux session (no incompatible env payloads)
- [x] 3.4 Update CAO prompt send/output polling to use typed terminal status + typed output response parsing
- [x] 3.5 Update CAO stop/cleanup logic and docs (delete terminal + session, document tmux requirement and provider mapping)

## 4. Quality Gates

- [x] 4.1 Run `ruff format .`, `ruff check .`, and fix lint issues from the refactor
- [x] 4.2 Run `mypy src` and fix typing issues introduced by boundary model changes
- [x] 4.3 Run `pytest` (where available) and ensure runtime + CAO unit tests pass

## 5. Live Demo Scripts (Manual E2E, Real Providers)

- [x] 5.1 Add tutorial-pack demo suites under `scripts/demo/<purpose-slug>/` following `context/instructions/explain/make-api-tutorial-pack.md` (step-by-step README + one-click `run_demo.sh` + temporary workspace + verification via `expected_report/` + sanitizer or explicit verifier)
- [x] 5.2 Implement a Codex CAO demo that launches a CAO-backed Codex session, sends a prompt, and prints a non-empty response (uses creds from `agents/brains/api-creds/`)
- [x] 5.3 Implement a Claude Code CAO demo that launches a CAO-backed Claude Code session, sends a prompt, and prints a non-empty response (uses creds from `agents/brains/api-creds/`)
- [x] 5.4 Implement a Gemini demo (non-CAO backend) that starts a Gemini session, sends a prompt, and prints a non-empty response (uses creds from `agents/brains/api-creds/`)
- [x] 5.5 Ensure demos avoid secret leakage (never echo `vars.env` contents; log only env var names and high-level progress)
- [x] 5.6 Implement per-demo SKIP behavior: if credentials are missing/invalid or connectivity is unavailable/lost, report SKIP with a clear reason and exit 0 for that demo; exit non-zero only for unexpected/bug failures
- [x] 5.7 Ensure CAO demos start `cao-server` and manage its lifecycle for demo testing (auto-start when needed; stop only if started by the demo)

## 6. Demo-Found Bugfixes

- [x] 6.1 Fix CAO runtime-generated profile frontmatter to include required `description` field (align with vendored CAO `AgentProfile` model)
- [x] 6.2 Update CAO demo SKIP classification: do not treat generic `CAO API error` as connectivity; skip only for missing/invalid creds or true connectivity issues
- [x] 6.3 Fix headless backend error reporting so non-zero exit codes surface the underlying stderr (avoid masking missing auth as "missing session_id")
- [x] 6.4 Increase CAO backend default timeout so `create_terminal` can complete provider initialization (avoid 15s client-side timeouts)
