## Context

This repo now has a canonical component layout under `agents/` and a brain builder that can construct a fresh tool home from `{tool, skills, config profile, credential profile}` and emit a secret-free manifest. What is still missing is a repo-owned Python runtime that can:

- launch and drive non-CAO interactive sessions using backend-appropriate lifecycle semantics (long-lived process when supported; resumable headless CLI turns when not), and
- optionally run the same sessions under CAO (tmux + REST), without making CAO a hard dependency.

We also want the `agents/roles/<role>/system-prompt.md` role packages to be used as the *initial instructions* for a running tool session (tool-specific injection when supported, otherwise a first-turn bootstrap message).

Constraints:

- Keep the core API CAO-agnostic; CAO is an optional backend.
- Do not introduce credential profile locking in this runtime (credential sharing is allowed; ensuring safe sharing is the caller’s responsibility).
- Avoid embedding or persisting secrets in manifests or controller artifacts.

## Goals / Non-Goals

**Goals:**

- Provide a Python module that composes `{brain, role}` into a backend-agnostic launch plan.
- Support a non-CAO interactive mode where callers can send multiple prompts across one logical session.
  - Codex uses a long-lived process backend (`codex app-server`, JSON-RPC over stdio).
  - Claude/Gemini use resumable headless invocations (`json`/`stream-json` with persisted `session_id` and `--resume`).
  - Do not rely on PTY/terminal scraping in this version.
- Support an optional CAO backend that:
  - launches terminals via CAO REST only (no direct imports from CAO runtime code required),
  - installs a CAO agent profile generated at runtime from a repo role package (no committed CAO profiles).
- Apply tool adapter launch contracts:
  - select the correct tool home (e.g., `CODEX_HOME`)
  - apply allowlisted credential env vars at launch time
- Ensure runtime-generated structured artifacts (manifests/configs) are schema-validated on write and read.
- Keep JSON Schema assets versioned in the runtime package under `src/gig_agents/.../schemas/`.
- Keep the API usable if CAO is swapped out (ports/adapters).

**Non-Goals:**

- Full multi-agent team orchestration policy (covered by `agent-team-orchestration-runtime`).
- Implementing CAO server internals or re-implementing provider parsing.
- Credential locking / coordination; concurrency controls are out of scope.
- Multi-host or distributed execution.

## Decisions

### 1) Ports-and-adapters split (CAO is optional)

Define a small core API in a CAO-agnostic package (domain types + interfaces), with backend implementations:

- **Core**: load `{brain recipe / blueprint, role}`, produce a `LaunchPlan`, and expose a stable `InteractiveSession` interface (streaming output + interrupt/terminate).
- **Backends**:
  - `codex_app_server`: non-CAO interactive backend (long-lived, structured protocol).
  - `claude_headless`: non-CAO backend using repeated `claude -p` invocations with `json|stream-json` and `--resume <session_id>`.
  - `gemini_headless`: non-CAO backend using repeated `gemini -p` invocations with `json|stream-json` and `--resume <session_id>`.
  - `cao_rest`: CAO backend (terminals via REST; role injected via generated CAO agent profile).
  - future: additional stdio-based backends, without changing the core surface.

Rationale: isolates CAO coupling, preserves reusability if CAO is swapped out, and supports multiple tools with minimal branching.

### 2) `InteractiveSession` is streaming + interruptible with backend-defined continuity

The core `InteractiveSession` interface must support:

- streaming output/events so callers can observe progress, and
- an explicit interrupt/terminate capability so callers can stop in-flight backend work early (e.g., send an interruption key when applicable, or terminate the underlying process).
- backend-defined continuity:
  - persistent-process backends keep one subprocess across turns,
  - resumable headless backends may spawn one subprocess per turn but MUST preserve one logical session identity via persisted resume fields (for example `session_id`).

Rationale: this preserves a single caller-facing session model while accommodating tool protocol differences (long-lived vs resumable headless).

### 3) Role injection as “first prompt” via tool-specific mechanisms

Represent role application as part of the launch plan, but materialize it differently per backend/tool:

- **Codex app-server**: pass role text as `thread/start.developer_instructions` so it is applied before any user turn.
- **Claude headless**: on session bootstrap, prefer `--append-system-prompt` for native role injection; if unavailable, send a clearly delimited bootstrap message before the first real user prompt.
- **Gemini headless**: send role text as a clearly delimited bootstrap message on session bootstrap, then continue resumed turns without replaying role text.
- **CAO**: generate a CAO agent profile whose Markdown body is the role prompt; CAO providers inject that into the underlying tool (Codex via `developer_instructions`, Claude via `--append-system-prompt`, etc.).
- **Fallback transports**: send a bootstrap message as the first user input, clearly delimited, when no native role/system prompt injection exists.

Rationale: “role as first prompt” must be reliable even when tools differ.

### 4) Runtime-generated CAO agent profiles (no committed files)

CAO identifies an agent profile by name and loads it from its local agent store (`~/.aws/cli-agent-orchestrator/agent-store/<name>.md`). CAO REST has no profile creation endpoint.

Decision: the CAO backend will generate a profile file at runtime from a repo role package and write it into CAO’s local agent store directory (or a configured override path), then launch terminals referencing that profile name. Profiles are unique per session (append-only), with naming schema `<role_name>_<timestamp>_<uuid4hex>`. Git-tracked role prompts are treated as templates: per-session context may be represented by prepending/appending additional text and/or altering parameterizable strings inside the role prompt.

Rationale: meets the “generated at runtime” requirement without requiring `cao install` as a dependency, keeps CAO-coupled behavior isolated, and avoids overwriting/racing on a single per-role profile file. Cleanup is manual (no automatic GC).

### 5) Persist a session manifest JSON (audit/resume/stop)

Persist a session manifest JSON (session handle) alongside the brain manifest so sessions can be audited/resumed/stopped without requiring in-memory state in the caller.

Minimum session manifest fields:

- common: `schema_version`, `backend`, `tool`, `role_name`, `created_at_utc`, `working_directory`, `brain_manifest_path`
- codex app-server: process/thread reconnect fields (for example PID/process start metadata + thread/session identifiers)
- headless Claude/Gemini: `session_id`, turn counters, and role-bootstrap status (to avoid re-injecting role on resumed turns)
- CAO: `api_base_url`, `session_name`, `terminal_id`, generated profile identity, artifact paths

Rationale: the brain manifest is about “what was built”; a session handle captures “what is running” (backend identity, reconnect fields, artifact paths).

### 6) No credential locking

Do not implement locks under `<runtime_root>/locks/`. Allow launching multiple sessions that reference the same credential profile.

Rationale: this runtime should not refuse launches; safe sharing is the caller’s responsibility.

### 7) CAO env isolation: per-agent tmux sessions (never share)

CAO REST does not accept per-terminal env vars; env is inherited from the tmux session/window environment. The CAO backend will support:

- a “one tmux session per launched agent” mode for strict env isolation.

Rationale: avoids racy env behavior; this runtime will not share tmux sessions between agents.

### 8) CAO messaging semantics: poll status, direct input only, no inbox

For CAO-managed agents, this runtime will:

- only send input when the terminal status is `idle` or `completed` (poll via `GET /terminals/{id}`),
- fetch output only after the request is fully processed (no mid-generation output consumption for this backend),
- not use CAO’s inbox mechanism (queueing/syncing/locking for concurrent callers is external to this runtime),
- use a default timeout of 15s (configurable),
- return agent/tool errors to the caller as error messages and let the caller decide how to proceed.

Rationale: this keeps the CAO backend simple and avoids relying on CAO inbox semantics; concurrency policy belongs outside this single-session runtime.

### 9) Shared CAO REST client module across runtimes

Implement the CAO REST client as a shared module used by both `agent-brain-launch-runtime` and `agent-team-orchestration-runtime`.

Rationale: avoids duplicating endpoint shapes, timeouts, error handling, and test scaffolding across two runtimes.

### 10) Claude/Gemini headless contract for deterministic resume

For non-CAO Claude/Gemini backends, this runtime will:

- invoke headless mode (`-p`) with machine-readable output (`--output-format json|stream-json`),
- parse machine output from `stdout` and treat `stderr` as diagnostics,
- capture and persist backend-issued `session_id` from the bootstrap turn,
- send follow-up turns with `--resume <session_id>`,
- treat missing/unparseable `session_id` on bootstrap as a launch error for resumable mode,
- enforce resume invariants that depend on tool semantics (for Gemini: same project/working directory).

Rationale: this yields deterministic multi-turn continuity without relying on undocumented long-lived interactive control protocols.

### 11) Schema-validated runtime manifests/configs with in-package JSON Schemas

All runtime-generated structured artifacts (for example session manifests and generated runtime config payloads) must be validated against JSON Schema:

- validate before persisting generated files,
- validate when loading/resuming from persisted files,
- fail fast with explicit validation errors (field path + reason) instead of silently accepting invalid structure.

Schema location and packaging:

- store schema files under the runtime Python package at `src/gig_agents/.../schemas/`,
- version schemas explicitly (for example `session_manifest.v1.schema.json`),
- include schema version fields in generated artifacts so validators select the correct schema.

Rationale: schema-first artifacts improve resume reliability, forward compatibility, and auditability, especially across multiple backends.

## Risks / Trade-offs

- **CAO store path coupling**: writing generated profiles into CAO’s local agent store assumes a stable path. → Mitigation: allow override via config and keep the logic localized to the CAO backend.
- **Tool protocol variance**: not all tools have a stable long-lived stdio protocol, or a headless CLI mode with resumable sessions. → Mitigation: start with `codex app-server`, keep headless CLI support adapterized, and avoid PTY/terminal scraping.
- **Headless output schema drift**: Claude/Gemini JSON/JSONL event shapes can evolve. → Mitigation: isolate per-tool parsers, prefer tolerant extraction for session/result fields, and cover with fixture tests.
- **Runtime artifact schema drift**: generated manifest/config shapes may diverge between writers/readers over time. → Mitigation: keep versioned JSON Schemas in-package, validate on write/read, and fail fast with actionable errors.
- **Secret handling**: env-based creds must be applied to processes but should not leak into manifests/logs. → Mitigation: manifests remain secret-free; runtime avoids logging secret values and only logs env var names.
- **Env isolation under CAO**: per-agent tmux sessions increase process/session count and can be operationally heavier. → Mitigation: keep lifecycles explicit, and persist session handles for audit/cleanup.

## Migration Plan

- Introduce the new runtime module alongside existing tooling.
- Move higher-level orchestrators (including the CAO-based agent-team runtime) to call this module to build+launch brains consistently.
- Keep roles canonical under `agents/roles/` and avoid committing CAO profiles.
