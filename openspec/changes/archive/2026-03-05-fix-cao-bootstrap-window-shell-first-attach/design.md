## Context

CAO-backed runtime sessions currently use a two-step startup sequence:

1. Runtime pre-creates a detached tmux session to set session-scoped env vars
   (including `AGENTSYS_MANIFEST_PATH`).
2. Runtime calls CAO `POST /sessions/{session_name}/terminals` to create the
   provider terminal.

Because CAO creates a new window in an existing session for that endpoint, the
session ends up with a bootstrap shell window plus the real agent window. In
manual workflows, first attach often lands on the shell window.

Implementation note: CAO terminal creation returns a `Terminal` object whose
`name` field is the tmux window name created by CAO. The runtime can use this
field directly instead of an additional `GET /terminals/{terminal_id}` call.

Constraints:
- We must preserve session-level env propagation semantics.
- CAO API does not currently provide a "reuse existing window" parameter.
- Startup should not become brittle because of optional cleanup behavior.

## Goals / Non-Goals

**Goals:**
- Ensure successful CAO-backed launches do not leave a user-visible bootstrap
  shell window as the default attach experience.
- Preserve existing AGENTSYS identity and tmux manifest-pointer contracts.
- Keep startup robust by making cleanup best-effort and diagnosable.

**Non-Goals:**
- Changing upstream CAO API contracts.
- Reworking CAO terminal creation flow into a different backend model.
- Implementing aggressive session/window reconciliation beyond startup hygiene.

## Decisions

### 1) Keep pre-create tmux session flow for env propagation

We keep the current runtime-first tmux session creation and env injection step.
This remains necessary because CAO terminal creation does not accept per-terminal
env payloads.

Alternatives considered:
- Let CAO create the session directly: rejected because runtime cannot reliably
  inject required session env before provider launch.

### 2) Record bootstrap window immediately after session creation

After creating the tmux session, capture bootstrap window identity (prefer a
stable tmux `window_id`; keep window name/index for diagnostics).

Implementation detail: record `window_id` (and optionally name/index) via tmux
introspection (for example `tmux list-windows -t <session> -F ...`) instead of
assuming an index like `0`.

Alternatives considered:
- Assume bootstrap is always `window 0`: rejected because tmux index defaults
  are configurable and brittle.

### 3) After CAO terminal creation, select the agent window and prune only the recorded bootstrap window

Once CAO returns the created terminal, use `terminal.name` as the tmux window
name for the agent terminal.

To fix the "shell-first attach" behavior even when pruning fails, best-effort
resolve the agent tmux `window_id` from `terminal.name` (bounded retry), then
select that `window_id` as the tmux session's current window. Finally, if the
recorded bootstrap `window_id` is different from the resolved agent `window_id`,
kill only the recorded bootstrap window.

Notes:
- Prefer `window_id` targeting for both `select-window` and `kill-window` to
  avoid ambiguity from index/name targeting.
- Do not add a `GET /terminals/{id}` call solely to resolve the window name;
  `create_terminal(...)` already returns `terminal.name`, and `shadow_only`
  flows intentionally avoid `GET /terminals/{id}` status paths.

Alternatives considered:
- Kill all non-terminal windows: rejected as too aggressive and unsafe if other
  windows appear in the same session.
- Skip cleanup and rely on docs/instructions: rejected due recurring user
  confusion and accidental teardown.
- Only select the agent window (no pruning): rejected because the bootstrap
  shell window remains user-visible and still invites accidental interaction.

### 4) Cleanup is best-effort and non-fatal

If bootstrap pruning fails, session launch still succeeds. Emit explicit warning
diagnostics so operators can diagnose residual two-window sessions. For the
CLI path, prefer a stderr `warning:` line while keeping `start-session` JSON
output stable.

Alternatives considered:
- Fail launch on cleanup error: rejected because the session is otherwise usable
  and hard-fail would reduce reliability.

### 5) Keep cleanup helpers in `cao_rest.py` for now

Implement tmux cleanup helpers alongside existing CAO tmux session helpers in
`backends/cao_rest.py`. Defer shared tmux utility extraction until the broader
`unify-headless-tmux-backend` change is ready to consolidate tmux behavior
across backends.

## Risks / Trade-offs

- [Risk] Bootstrap-window identity may become stale between capture and prune.
  -> Mitigation: verify target existence and ensure it is not the resolved
  terminal window before kill.
- [Risk] Terminal window resolution could fail transiently after creation.
  -> Mitigation: keep cleanup best-effort and log structured warning details.
- [Risk] Additional tmux calls add startup complexity.
  -> Mitigation: isolate logic in small helper functions with focused tests.

## Migration Plan

- No manifest schema migration is required.
- Roll out as runtime behavior change for new CAO-backed starts only.
- Validate via unit tests and a manual attach check (`tmux list-windows` then
  `tmux attach`) in CAO-backed flows.

## Open Questions

- None. Decisions are captured in `discuss/discuss-20260305-091708.md`.
