## Context

The brain launch runtime currently supports three distinct execution shapes:

- CAO-backed sessions (`backend=cao_rest`): tmux-backed; the runtime creates a tmux session and publishes environment + `AGENTSYS_MANIFEST_PATH` so users can attach to tmux and the runtime can resolve `--agent-identity` names via tmux.
- Claude/Gemini headless sessions (`backend=claude_headless`, `backend=gemini_headless`): per-turn subprocess invocations (`<tool> -p ... --resume <session_id> --output-format stream-json`) via the shared headless runner implementation, with continuity via a persisted `session_id` in the session manifest.
- Codex local sessions (`backend=codex_app_server`): a long-lived `codex app-server` subprocess speaking JSON-RPC over stdio. This backend cannot be resumed after a runtime restart because the stdio channel is not recoverable from a persisted manifest.

Name-based `--agent-identity` resolution already uses tmux session environment (`AGENTSYS_MANIFEST_PATH`) to locate a manifest path, but validation is currently CAO-only (`backend=cao_rest`).

This change unifies headless Claude Code, headless Gemini, and headless Codex on one pattern:
each headless agent owns a tmux session (inspectable by users) and each prompt
turn is executed as a CLI invocation inside that tmux session, with continuity
provided by a tool-native resume identifier stored in the session manifest.

Constraints:

- We must preserve the existing CAO/tmux contract used for TUI agents: tmux identity naming rules, `AGENTSYS_MANIFEST_PATH` publication, and user inspectability.
- Headless Codex must avoid tool-specific daemon/server modes (no `codex app-server`).
- Session continuity must survive runtime restarts (manifest-only resume).
- Avoid large-scale schema churn unless it pays its way; prefer additive persisted state in `backend_state` when possible.

## Goals / Non-Goals

**Goals:**

- Make Claude headless and Codex headless share the same lifecycle model:
  - a stable tmux identity per agent session (`AGENTSYS-...`)
  - per-turn CLI invocations inside tmux
  - continuity via a persisted tool resume id
- Make Gemini headless match the same tmux-backed lifecycle (keeping its existing `--resume` semantics).
- Implement Codex headless using `codex exec --json` and `codex exec --json resume <thread_id>`.
- Extend name-based `--agent-identity` resolution to support tmux-backed headless sessions (not CAO-only).
- Share tmux/session identity utilities between CAO and headless backends (single place for tmux creation/env publication).

**Non-Goals:**

- Change CAO parsing/extraction behavior (`cao_only` vs `shadow_only`) or shadow parser logic.
- Provide real-time streaming events to the CLI (runtime continues to return event lists per turn).
- Solve multi-host orchestration or distributed tmux management.
- Rework tool prompt/role packages beyond what is required to keep current role injection semantics acceptable.

## Decisions

### Decision: Treat tmux as the standard “agent container” for tmux-backed backends

We introduce a shared tmux container contract used by:

- `cao_rest` (already tmux-backed today)
- headless Claude, Gemini, and Codex (new behavior)

The container responsibilities are:

- Allocate a canonical tmux session name using existing `AGENTSYS-` rules.
- Create the tmux session.
- Provide shared primitives for publishing key environment variables into tmux session environment for:
  - tool execution (allowlisted credentials + tool home selector)
  - session binding (`AGENTSYS_MANIFEST_PATH`)
  - human inspection (optional convenience vars like `AGENTSYS_TOOL`, `AGENTSYS_RESUME_ID`)
- Keep launch-environment composition policy backend-specific (shared module handles tmux mechanics; each backend owns env allowlists/precedence).

Rationale:

- This matches how CAO/TUI agents are already managed, so headless and TUI sessions share a debuggable substrate.
- It enables a consistent “attach to agent” workflow (`tmux attach -t AGENTSYS-...`) across backends.

Alternatives considered:

- Keep headless as direct subprocess and “mirror” env into tmux only for inspection.
  - Rejected: violates the requirement that headless agents run inside tmux, and produces two sources of truth.
- Extract one fully shared tmux+env policy stack for all backends.
  - Rejected: over-couples backend-specific env/security policy and increases regression risk.

### Decision: Replace Codex app-server backend with Codex exec JSONL + resume id

Codex headless will be implemented with:

- new session: `codex exec --json <prompt>`
- resume: `codex exec --json resume <thread_id> <prompt>`

The persisted resume id is the Codex thread/session identifier extracted from:

- JSONL events, typically the `thread.started` event containing `thread_id`.

Rationale:

- Removes the non-resumable stdio protocol dependency (`codex app-server`).
- Aligns Codex with the same “CLI per turn + resume id” lifecycle used by Claude headless.
- Uses a stable, tool-supported CLI contract rather than an internal server mode.

Alternatives considered:

- Keep `codex app-server` as the default and add a separate codex headless mode.
  - Rejected: does not satisfy the “unify headless pattern” requirement and keeps the non-resumable default.

### Decision: Inject Codex role prompt via config override (`-c developer_instructions=...`)

For Codex headless turns, role guidance will be injected through Codex config override
(`developer_instructions`) rather than mutating the first user prompt text.

Rationale:

- Preserves role-channel semantics (developer guidance remains developer guidance).
- Keeps user prompt payload stable across first turn and resume turns.
- Avoids hidden behavior drift from bootstrap prompt rewriting.

Alternatives considered:

- Inject role text as first-turn bootstrap user message.
  - Rejected: conflates channels and complicates prompt provenance/debugging.

### Decision: Execute headless turns inside tmux using file-based capture (stdout/stderr) + completion signaling

For each turn, the runtime will:

- build the CLI argv for the tool and turn (including `resume`/`--resume` when present)
- run the command inside tmux (dedicated runner window or per-turn window)
- capture outputs into per-turn files under the runtime session root:
  - `stdout.jsonl` (machine-readable events)
  - `stderr.log` (diagnostics)
  - `status.json` or `exitcode` marker
- wait for completion via either:
  - `tmux wait-for` channel signaling (primary contract), or
  - polling for the status marker file (fallback for signaling edge cases)

Rationale:

- Capturing stdout/stderr separately avoids pseudo-terminal interleaving that would corrupt JSONL.
- File-based capture supports postmortem inspection and reproducible debugging.

Alternatives considered:

- Use `tmux pipe-pane` and parse capture-pane output.
  - Rejected: mixes stdout/stderr in a PTY and includes shell prompts/ANSI, making JSON parsing brittle.

### Decision: Persist tmux identity for headless sessions without requiring an immediate manifest schema bump

We persist the tmux session name for headless backends in `backend_state`, for example:

- `backend_state.tmux_session_name = "AGENTSYS-..."`
- `backend_state.session_id = "<tool resume id>"` (Codex stores its `thread_id` here for `backend=codex_headless`)

This keeps `session_manifest.v2` usable while still enabling:

- validating name-based resolution against the addressed tmux session
- recreating or reattaching behavior on resume

Rationale:

- Avoids a coordinated schema migration in the first iteration.
- Allows incremental tightening later (for example moving to a first-class typed section + schema bump).

Alternatives considered:

- Bump to `session_manifest.v3` immediately and add a first-class `tmux` section.
  - Deferred: valuable, but higher migration cost; can be a follow-up once the runtime behavior stabilizes.

### Decision: Preserve tmux session on headless `stop-session` by default

For tmux-backed headless sessions, default `stop-session` ends runtime control but keeps the
tmux session for inspectability and postmortem debugging.

An explicit force-cleanup path is required for automation/CI workflows that prioritize
resource cleanup.

Rationale:

- Preserves the unified tmux-inspectable contract between TUI/CAO and headless paths.
- Supports rollout debugging without losing immediate terminal/session context.

### Decision: Deprecate `codex_app_server` using one bounded override window

This change switches the default non-CAO Codex backend to `codex_headless` immediately.

`codex_app_server` remains available only as an explicit override for one deprecation window,
with explicit sunset criteria (stability + test coverage + docs parity), then removal in a
follow-up change.

Rationale:

- Immediate architectural convergence with controlled rollback during stabilization.
- Avoids abrupt breakage while preventing indefinite dual-maintenance drift.

### Decision: Generalize name-based identity validation to all tmux-backed backends

Name-based `--agent-identity` validation is not CAO-only in this change.

For tmux-backed backends, resolved manifests must persist and match canonical tmux session name
using backend-appropriate fields (for example `cao.session_name` for CAO and
`backend_state.tmux_session_name` for headless).

Rationale:

- Delivers identity-resolution parity across tmux-backed backends.
- Preserves fail-fast mismatch detection when name resolution points to stale/incorrect manifests.

## Risks / Trade-offs

- [tmux dependency for headless] → Mitigation: fail fast with actionable error when `tmux` is missing; document tmux as required for Claude/Gemini/Codex headless.
- [Secrets exposed via tmux session env] → Mitigation: only publish allowlisted credential vars + required tool selectors; avoid dumping full `os.environ`.
- [Turn window/log proliferation] → Mitigation: use a stable `runner` window by default; optionally rotate per-turn artifacts and keep only N windows.
- [Codex exec output contract drift] → Mitigation: keep resume-id extraction robust (search events for `thread_id`), and preserve stderr logs for debugging.
- [Role injection differences for Codex exec vs app-server] → Mitigation: use Codex config override role injection (`-c developer_instructions=...`) to preserve role-channel semantics without rewriting the user prompt; test and document behavior differences.
- [Default stop preserves tmux may leave stale sessions] → Mitigation: explicit force-cleanup path, idempotent cleanup behavior, and clear docs on stopped-vs-deleted semantics.

## Migration Plan

1. Extract shared tmux utilities (session creation, command execution, env publication primitives, identity allocation) into a runtime-shared module used by CAO and headless, while keeping env composition policy backend-specific.
2. Add a new Codex headless backend using `codex exec --json` + resume id extraction, executed inside tmux.
   - Use Codex config override role injection (`developer_instructions`) for headless role prompt handling.
3. Port Claude headless execution from direct subprocess to tmux-executed CLI turns (retain the same `--resume` and output parsing behavior).
   - Also port Gemini headless to the same tmux execution path.
4. Update agent identity resolution:
   - allow name-based resolution for tmux-backed headless manifests (not CAO-only)
   - validate resolved manifest matches the addressed tmux session identity
5. Change default Codex non-CAO backend selection from `codex_app_server` to the new Codex headless backend.
6. Keep `codex_app_server` available as explicit opt-in fallback for one deprecation window with documented sunset criteria; remove in follow-up once criteria are met.
7. Implement/ship headless stop semantics: default preserve tmux session, explicit force-cleanup path for automation.

Rollback strategy:

- Allow forcing `backend=codex_app_server` explicitly during the bounded transition window.
- Preserve existing manifest parsing for older sessions; require new sessions for the unified headless behavior.

## Resolved Questions

All blocking open questions for this change were resolved in:

- `openspec/changes/unify-headless-tmux-backend/discuss/discuss-20260304-155810.md`

Accepted defaults in this change:

- Keep `session_manifest.v2` with additive `backend_state` fields (defer `v3`).
- Codex role injection uses config override (`developer_instructions`) rather than bootstrap prompt rewriting.
- Headless `stop-session` preserves tmux by default; automation uses explicit force-cleanup.
- Shared module scope is tmux primitives/identity; env policy stays backend-specific.
- Default Codex backend switches now; `codex_app_server` is explicit opt-in for one deprecation window.
- Name-based validation generalizes from CAO-only to all tmux-backed backends with persisted canonical tmux name checks.
- Turn completion uses `tmux wait-for` as primary with marker polling fallback.
