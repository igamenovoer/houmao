## Context

`brain_launch_runtime` session-control commands currently resolve `agent_def_dir` before they resolve a name-based `--agent-identity`. That makes control flows like `stop-session --agent-identity chris` depend on caller-provided `--agent-def-dir`, `AGENTSYS_AGENT_DEF_DIR`, or a cwd-derived default even though the addressed tmux session already publishes runtime metadata into its own tmux environment.

The runtime already uses tmux environment state as the source of truth for name-based manifest discovery via `AGENTSYS_MANIFEST_PATH`. This change extends that tmux-published contract with `AGENTSYS_AGENT_DEF_DIR` so name-addressed session control can recover the same agents tree that launched the session.

## Goals / Non-Goals

**Goals:**
- Let name-based tmux-backed control commands omit `--agent-def-dir`.
- Treat the addressed tmux session as the source of truth for agent-definition-root recovery.
- Keep explicit `--agent-def-dir` as an override for debugging, migration, and unusual operator flows.
- Update in-repo name-addressed operator flows to rely on the same tmux-session-derived default instead of continuing to pass explicit `--agent-def-dir`.
- Document the split resolution model clearly so operators understand when ambient defaults still apply and when tmux session state becomes the default.
- Avoid manifest schema churn when the needed source-of-truth data already exists in tmux session environment state.

**Non-Goals:**
- Removing `--agent-def-dir` from the CLI surface entirely.
- Changing manifest-path-based control flows to recover `agent_def_dir` from unrelated ambient defaults.
- Reworking session manifests to persist a new `agent_def_dir` field in this iteration.
- Changing start-session recipe/build semantics outside the tmux-env publication contract.

## Decisions

### 1. Publish `AGENTSYS_AGENT_DEF_DIR` into tmux session environment for all tmux-backed launches

Tmux-backed headless and CAO-backed launches will publish:
- `AGENTSYS_MANIFEST_PATH`
- `AGENTSYS_AGENT_DEF_DIR`

The published `AGENTSYS_AGENT_DEF_DIR` value must be an absolute path to the agent-definition root used for the session launch.

The effective `agent_def_dir` will be carried explicitly through the runtime start/resume path rather than persisted into `LaunchPlan`, launch-plan metadata, or the session manifest. `start_runtime_session()` and `resume_runtime_session()` already compute or receive the effective agent-definition root; this change will thread that value into `_create_backend_session()` and then into the tmux-backed backend session objects that actually publish tmux session environment state.

Tmux-backed backend session objects will use that backend-held value whenever they publish or re-publish tmux environment pointers. That keeps start and resume behavior aligned without introducing manifest schema churn.

Why this over storing it only in the manifest:
- The runtime already trusts tmux env as the discovery path for name-based identity resolution.
- This keeps the change small and aligned with the existing `AGENTSYS_MANIFEST_PATH` design.
- It avoids a manifest schema bump for a recovery path that is only needed for tmux-name addressing.

Alternatives considered:
- Persist `agent_def_dir` in the session manifest only: rejected for this iteration because name-based control already depends on tmux env, so manifest-only storage would still require more cross-path wiring.
- Infer `agent_def_dir` from manifest location or repo layout: rejected because it is brittle and not guaranteed by contract.
- Add `agent_def_dir` to `LaunchPlan` or `LaunchPlan.env`: rejected because it would either blur the boundary between launch metadata and persisted manifest payloads or rely on env persistence/redaction behavior that is not the source-of-truth contract for this change.

### 2. Name-based control resolves identity first, then derives effective `agent_def_dir`

For `send-prompt`, `send-keys`, and `stop-session`, command handling will change order:
1. Parse `--agent-identity`.
2. If path-like, keep the current manifest-path flow.
3. If name-based and `--agent-def-dir` is provided, use the explicit CLI override.
4. If name-based and `--agent-def-dir` is omitted, resolve the tmux session first and recover both:
   - session manifest path from `AGENTSYS_MANIFEST_PATH`
   - agent-definition root from `AGENTSYS_AGENT_DEF_DIR`
5. Resume/control the session using that resolved pair.

The existing `AgentIdentityResolution` dataclass in `runtime.py` will be extended to carry the resolved `agent_def_dir` for the name-based fallback path instead of introducing a second resolution type. Manifest-path resolution will continue to use the same type with no tmux-derived `agent_def_dir` attached.

When explicit `--agent-def-dir` is provided for a name-based control command, the runtime will still resolve the manifest path from the addressed tmux session, but it will use the explicit CLI path as the effective agent-definition root. That keeps legacy tmux sessions operable even when they predate `AGENTSYS_AGENT_DEF_DIR`.

Why this over keeping current ordering:
- The whole benefit of the new env var is lost if command handlers still resolve `agent_def_dir` before session identity.
- The session-specific tmux env is a better source of truth than caller cwd defaults for an already-running agent.

Alternatives considered:
- Keep current ordering and use tmux env only as a low-priority fallback: rejected because it preserves the current confusing coupling to caller defaults.

### 3. Missing or invalid tmux `AGENTSYS_AGENT_DEF_DIR` is a hard error for name-based fallback

For name-based session control with omitted `--agent-def-dir`, the runtime will fail explicitly when tmux recovery finds a missing, blank, non-absolute, or nonexistent `AGENTSYS_AGENT_DEF_DIR`.

Why this over silently falling back to caller env/defaults:
- Silent fallback can point control operations at the wrong agents tree.
- The operator expectation for name-addressed control is "act on that live session," not "guess from my cwd."
- Hard failure surfaces stale or pre-change sessions clearly.

Alternatives considered:
- Fall back to `AGENTSYS_AGENT_DEF_DIR` from the caller environment or `<pwd>/.agentsys/agents`: rejected because it reintroduces ambiguity for the exact flow this change is trying to fix.

### 4. Manifest-path control remains unchanged in this iteration

When `--agent-identity` is path-like, the runtime will keep the current explicit/ambient `agent_def_dir` resolution contract.

Why this scope boundary:
- The requested `AGENTSYS_AGENT_DEF_DIR` approach is specifically about leveraging tmux session state.
- Manifest-path addressing has no tmux session to interrogate.
- Keeping manifest-path behavior unchanged avoids expanding this change into manifest schema redesign.

### 5. In-repo name-addressed operator flows should adopt the new default path

In-repo wrappers and helper flows that target an already-running tmux-backed session by persisted agent name should omit explicit `--agent-def-dir` when invoking `send-prompt`, `send-keys`, and `stop-session`.

For this change, that explicitly includes the interactive CAO demo flow.

Why this over leaving wrappers unchanged:
- If in-repo callers keep passing explicit `--agent-def-dir`, the new default path remains unexercised in the main operator workflow.
- The interactive demo is the clearest real-user surface for validating that the session-owned agents root is now the default source of truth.

Alternatives considered:
- Change only the runtime behavior and leave wrappers passing `--agent-def-dir`: rejected because it weakens confidence in the new contract and leaves the repo's main manual workflow on the old path.

### 6. Docs must describe split resolution rules instead of one blanket precedence rule

Runtime and operator-facing docs should explicitly distinguish:
- build/start and manifest-path control flows, which still use ambient resolution (`CLI > AGENTSYS_AGENT_DEF_DIR > <pwd>/.agentsys/agents`), and
- name-based tmux-backed `send-prompt`, `send-keys`, and `stop-session`, which use `CLI` override first and otherwise recover `agent_def_dir` from the addressed tmux session.

Why this over editing examples only:
- The old single precedence statement becomes misleading once name-based control changes behavior.
- Operators need to understand why the same flag can still matter for build/start while becoming optional for active-session control.

### 7. CLI resolution paths should be split instead of hidden behind a mode flag

`build-brain`, `start-session`, and manifest-path control will keep the existing eager ambient resolution path for `agent_def_dir`.

Name-based `send-prompt`, `send-keys`, and `stop-session` will use a separate deferred resolution path that:
- resolves the addressed identity first,
- derives the effective `agent_def_dir` from either the explicit CLI override or tmux session environment, and
- passes the resolved pair into resume/control.

Why this over a shared mode-flagged helper:
- The behavior difference is real and important enough to remain visible at the call site.
- Separate helpers are easier to test and reason about than one resolver with internal mode branching.

## Risks / Trade-offs

- [Older tmux-backed sessions lack `AGENTSYS_AGENT_DEF_DIR`] → Name-based control without explicit `--agent-def-dir` will fail clearly for those sessions; operators can still pass `--agent-def-dir` explicitly, and that override path must continue to work for legacy sessions.
- [More resolution logic in name-based control paths] → Extend the existing `AgentIdentityResolution` dataclass with the recovered `agent_def_dir` instead of duplicating ad hoc tuples or dicts per command.
- [tmux env becomes a stronger source of truth] → Validate the recovered value strictly (absolute path, existing directory) before using it.
- [tmux env can be lost across tmux-side disruptions] → Re-publish `AGENTSYS_AGENT_DEF_DIR` whenever resume reaches backend construction with an effective agent-definition root available; otherwise fail clearly and require explicit `--agent-def-dir`.
- [Manifest-path control still behaves differently] → Document the distinction explicitly so operators know why name-based control can omit `--agent-def-dir` but manifest-path control may still need it.
- [Some in-repo helpers may still pass explicit `--agent-def-dir`] → Audit demo/operator wrappers in this change and update them deliberately so behavior matches the documented contract.

## Migration Plan

1. Extend tmux-backed start/resume plumbing to carry the effective `agent_def_dir` into tmux-backed backend session objects and publish or re-publish `AGENTSYS_AGENT_DEF_DIR`.
2. Extend the existing `AgentIdentityResolution` type to carry recovered `agent_def_dir` for the name-based fallback path.
3. Split CLI resolution paths so build/start stay eager while name-based `send-prompt`, `send-keys`, and `stop-session` resolve identity first and then derive the effective `agent_def_dir`.
4. Update in-repo name-addressed operator flows, including the interactive demo wrapper path, to omit explicit `--agent-def-dir` when calling those runtime control commands.
5. Add tests for successful omission, explicit-override precedence including legacy sessions without `AGENTSYS_AGENT_DEF_DIR`, invalid/missing tmux env failures, and wrapper-level usage of the new default path.
6. Update runtime and operator docs/examples to show the split between ambient resolution and tmux-session-derived name-based control.

Rollback strategy:
- Remove tmux publication of `AGENTSYS_AGENT_DEF_DIR`.
- Restore the old command-handler ordering where `agent_def_dir` is always resolved from CLI/env/default before name resolution.

## Open Questions

- Whether a later follow-up should also persist `agent_def_dir` in session manifests so manifest-path control can become fully self-contained.
