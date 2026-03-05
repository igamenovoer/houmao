## 1. Package and Core Models

- [x] 1.1 Create a new Python package for brain launch runtime (CAO-agnostic core + backends)
- [x] 1.2 Define core dataclasses/interfaces (`LaunchPlan`, `InteractiveSession` with streaming output + interrupt/terminate, session config/result/event types)
- [x] 1.3 Implement loaders for repo inputs (brain recipe / blueprint, role package prompt)
- [x] 1.4 Define and persist a session manifest JSON (session handle) schema + read/write helpers (audit/resume/stop)
- [x] 1.5 Add JSON Schema assets for runtime-generated structured artifacts under `src/agent_system_dissect/.../schemas/` (at minimum session manifest and any persisted runtime config payloads)
- [x] 1.6 Implement shared schema validation helpers and enforce validation on artifact write/read paths (fail fast on schema errors)

## 2. Launch Plan Composition

- [x] 2.1 Implement a launch-plan builder that consumes the brain manifest + tool adapter contract (home selector, allowlisted env vars, executable/args)
- [x] 2.2 Implement role injection planning (tool-native injection when available; fallback bootstrap message)
- [x] 2.3 Ensure launch-plan materialization does not persist secret values (log only env var names + local paths)

## 3. Non-CAO Interactive Backends

- [x] 3.1 Implement a long-lived Codex session backend using `codex app-server` JSON-RPC over stdio
- [x] 3.2 Support starting a thread with role injected via `thread/start.developer_instructions`
- [x] 3.3 Support multi-turn prompting (multiple `turn/start` calls) and clean shutdown
- [x] 3.4 Expose streaming output/events for in-flight turns (even if the backend is internally event-based)
- [x] 3.5 Support interrupt/terminate for an in-flight Codex turn/session (best-effort cancel + process termination fallback)
- [x] 3.6 Implement a shared headless CLI runner for JSON/JSONL streaming (spawn subprocess, parse stdout events, surface stderr diagnostics)
- [x] 3.7 Implement a Claude headless backend using `claude -p` + `--output-format json|stream-json` and `--resume <session_id>` for follow-up turns
- [x] 3.8 Implement a Gemini headless backend using `gemini -p` + `--output-format json|stream-json` and `--resume <session_id>` for follow-up turns
- [x] 3.9 Persist and reload headless backend session state (`session_id`, working directory, role-bootstrap status, turn index) in the session manifest
- [x] 3.10 Ensure headless role application is bootstrap-only (native injection when available, otherwise bootstrap message) and is not replayed on resumed turns
- [x] 3.11 Support interrupt/terminate for in-flight headless turns via subprocess termination, with explicit outcome reporting

## 4. Optional CAO Backend (REST + Runtime Profiles)

- [x] 4.1 Implement a typed CAO REST client as a shared module (shared with `agent-team-orchestration-runtime`) (health/sessions/terminals/input/output/exit/delete and optionally inbox endpoints)
- [x] 4.2 Implement CAO agent profile generation from `agents/roles/<role>/system-prompt.md` as a per-session profile (markdown + YAML frontmatter, templating prepend/append/substitutions, naming `<role_name>_<timestamp>_<uuid4hex>`)
- [x] 4.3 Install generated CAO profiles at runtime into CAO local agent store (configurable path; default CAO home)
- [x] 4.4 Implement CAO launch that applies brain home selection + allowlisted credential env vars via per-agent tmux session env strategy (never share tmux sessions)
- [x] 4.5 Implement CAO prompt send that polls terminal status until `idle|completed`, uses direct input only (no inbox), waits for completion with default timeout=15s, and then fetches output (post-completion only)

## 5. CLI Surface

- [x] 5.1 Add `python -m ...` CLI entrypoint for: build brain, start session (local/CAO), send prompt, stop session
- [x] 5.2 Add CLI flags for runtime roots, working directory, backend selection, and CAO base URL

## 6. Tests, Docs, and Quality Gates

- [x] 6.1 Add unit tests for role loading plus role-injection planning (native vs bootstrap) and CAO profile rendering/installation (filesystem-only)
- [x] 6.2 Add unit tests for CAO REST client (mocked HTTP), launch-plan composition, headless JSON/JSONL parsing (including `session_id` extraction), and schema validation success/failure cases
- [x] 6.3 Add a short usage doc covering local sessions (`codex app-server`, Claude headless resume, Gemini headless resume) and CAO-backed sessions
- [x] 6.4 Ensure new code passes `ruff` format/check and `mypy src` (and `pytest` where available)
