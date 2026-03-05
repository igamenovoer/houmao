## 1. Shared tmux Container Utilities

- [x] 1.1 Extract tmux helpers (ensure tmux, list/create session, set env, cleanup, show-environment/has-session error normalization) into a shared runtime module used by both CAO launch and name-based agent-identity resolution
- [x] 1.2 Refactor `cao_rest` backend to use the shared tmux module (no behavior change)
- [x] 1.3 Add a small unit-test surface for tmux helper argument construction / error normalization (mock subprocess)
- [x] 1.4 Enforce module boundary: shared layer exposes tmux primitives/identity only; backend modules keep env composition policy (allowlists/precedence) backend-specific

## 2. tmux-backed Headless Turn Runner

- [x] 2.1 Define a tmux-based “run one CLI turn” runner that captures stdout/stderr into per-turn files
- [x] 2.2 Add completion signaling for turns (`tmux wait-for` as primary; status-marker polling fallback)
- [x] 2.3 Implement JSONL parsing from captured stdout into runtime `SessionEvent` list
- [x] 2.4 Extend resume-id extraction to support Codex exec events (`thread_id`) in addition to existing session id keys

## 3. Codex Headless Backend (`codex exec --json` + resume)

- [x] 3.1 Add a new backend kind for Codex headless CLI turns (e.g. `codex_headless`)
- [x] 3.2 Update launch-plan composition for Codex headless to inject `exec --json` (new) and `exec --json resume <thread_id>` (resume) argument shapes, including role injection via Codex config override (`-c developer_instructions=...`)
- [x] 3.3 Implement the Codex headless backend session using the tmux turn runner
- [x] 3.4 Persist Codex headless backend state (turn index + thread id + tmux session name) into the session manifest backend state
- [x] 3.5 Ensure Codex home bootstrap is applied for Codex headless sessions (same contract as CAO)

## 4. Claude Headless Migration to tmux Execution

- [x] 4.1 Update Claude and Gemini headless backends to execute turns inside tmux rather than direct subprocess
- [x] 4.2 Preserve existing Claude and Gemini role injection behavior (`--append-system-prompt` when applicable, and bootstrap-message behavior where used)
- [x] 4.3 Persist headless backend state (turn index + session id + tmux session name) into the session manifest backend state

## 5. Agent Identity Resolution for tmux-backed Headless Sessions

- [x] 5.1 Allow `start-session --agent-identity` for tmux-backed headless backends (not CAO-only)
- [x] 5.2 Publish `AGENTSYS_MANIFEST_PATH=<absolute manifest path>` into tmux env for tmux-backed headless sessions
- [x] 5.3 Update name-based resolution validation to accept tmux-backed headless manifests (not `backend=cao_rest` only)
- [x] 5.4 Add an explicit persisted tmux session name field for headless manifests (e.g. `backend_state.tmux_session_name`) and validate it on name-based resolution

## 6. Default Backend and Deprecation of `codex app-server`

- [x] 6.1 Switch default Codex non-CAO backend selection from `codex_app_server` to Codex headless
- [x] 6.2 Keep `codex_app_server` as an explicit opt-in override for one deprecation window (no hard cutover in this change)
- [x] 6.3 Define and document deprecation-window sunset criteria (stability, test coverage, docs parity) and target follow-up removal path
- [x] 6.4 Update docs (`docs/reference/brain_launch_runtime.md`) to describe Codex headless resume/defaults and temporary explicit `codex_app_server` override behavior

## 7. Tests and Validation

- [x] 7.1 Add unit tests for Codex headless command construction and resume behavior (new vs resume)
- [x] 7.2 Add unit tests for agent-identity name resolution acceptance for tmux-backed headless manifests
- [x] 7.3 Add an integration smoke test (optional/manual) that starts a tmux-backed headless session and runs two turns for Codex, Claude, and Gemini
- [x] 7.4 Add tests for deprecation-window backend selection behavior (default `codex_headless`, explicit `codex_app_server` override still honored)

## 8. Headless Stop/Cleanup Semantics

- [x] 8.1 Make tmux-backed headless `stop-session` preserve tmux session by default for inspectability
- [x] 8.2 Add explicit force-cleanup path to terminate tmux session for automation/CI workflows
- [x] 8.3 Add tests/docs clarifying and validating "stopped session" vs "deleted tmux container" behavior
