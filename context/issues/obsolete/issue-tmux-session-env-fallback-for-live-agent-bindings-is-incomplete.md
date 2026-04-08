# Issue: Tmux Session Env Fallback For Live Agent And Gateway Bindings Is Incomplete

> Obsolete as of 2026-04-08.
> Moved from `context/issues/known/` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Priority
P1 - The runtime design assumes managed agents and their gateways live inside tmux-backed runtime containers, but env-var resolution still behaves inconsistently across agent, skill, and gateway paths.

## Status
Open as of 2026-03-26.

## Summary

The current system already treats tmux session environment as authoritative for some runtime discovery paths, but it does not apply that same rule consistently when live agent or gateway code needs runtime-owned env vars.

The intended design assumption is:

- the managed agent runs inside a tmux-backed runtime session,
- the agent gateway runs inside that same tmux-contained runtime context or an attached tmux-owned companion surface,
- when runtime-owned code needs a specific env var and it is not present in the current process env, it should query the owning tmux session for that env var before concluding the value is unavailable.

That behavior is only partially implemented today.

Some flows already do the right thing:

- current-session runtime discovery reads `AGENTSYS_MANIFEST_PATH` from tmux session env
- some CLI/runtime artifact flows read selected vars from tmux session env

But other flows still assume the current process env is complete and current:

- gateway runtime reads some env values directly from `os.environ`
- mailbox skills are documented as if `AGENTSYS_MAILBOX_*` must already exist in the process env
- late mailbox mutation currently exposes cases where tmux session env has fresher values than the provider process env snapshot

This creates one contract gap: the repository increasingly treats tmux as the runtime container that owns mutable live session env, but env lookup behavior is not yet standardized around that assumption.

## What Is Wrong Today

The codebase currently mixes two different models.

### 1. Tmux-aware discovery exists

The runtime already resolves some critical session information from tmux session environment.

Example:

- `src/houmao/agents/realm_controller/runtime.py`
  - `_resolve_manifest_path_from_tmux_session()`

That path treats tmux session env as the live authority for `AGENTSYS_MANIFEST_PATH`.

### 2. Process-env-only reads still exist

Other runtime paths still read env directly from the current process and stop there.

Example:

- `src/houmao/agents/realm_controller/gateway_service.py`
  - `_optional_env_string()`
  - `GatewayServiceRuntime.__init__()`

The gateway runtime currently uses process env for several gateway-local bindings such as tmux window and pane metadata.

### 3. Mailbox skill guidance still assumes process env is the whole contract

Projected mailbox skill docs tell the agent to require `AGENTSYS_MAILBOX_*` bindings and re-read them before each action, but they do not define a tmux-session fallback rule when those vars are missing from the current process env.

Examples:

- `src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-filesystem/references/env-vars.md`
- `src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-stalwart/references/env-vars.md`

### 4. Late mailbox mutation exposes the inconsistency

In the real local-interactive mailbox run on 2026-03-26:

- late mailbox registration updated durable mailbox state,
- the owning tmux session could publish the refreshed mailbox bindings,
- the live provider process still lacked the new mailbox vars in its inherited process env,
- gateway notifier prompts could arrive while the agent still lacked a consistent live mailbox binding source.

That run showed the deeper issue clearly: mutable live env belongs to the tmux runtime container, but many agent-facing and gateway-facing paths still behave as if process env is the only live source.

## Why This Matters

This is not just a mailbox issue.

It affects the runtime contract more broadly:

- gateway discovery and execution context
- live mailbox binding refresh
- future tmux-contained backends such as planned tmux-backed `codex_app_server`
- any runtime-owned feature that expects env-based configuration to remain current after session startup

If the repository's core design assumption is "managed runtime lives in tmux," then env lookup must follow that boundary consistently.

Without that consistency, the system keeps drifting into split-brain behavior:

- durable state says one thing,
- tmux session env says another,
- current process env says a third or stale thing.

## Root Cause

The root cause is missing standardization, not one isolated bug.

The repository has already adopted tmux as:

- the live session container,
- the place where manifest pointers are published,
- the place where mutable session-scoped runtime env can be updated,
- the forward-looking home for all managed backends.

But the env lookup contract was never finished.

Today there is no single enforced rule like:

1. read the requested runtime-owned env var from current process env,
2. if missing and the session is tmux-backed, resolve the owning tmux session,
3. query that specific env var from tmux session env,
4. only then treat the value as unavailable.

Because that rule is not fully encoded, each subsystem makes its own assumption.

## Evidence

### 1. Runtime manifest discovery already uses tmux env

- `src/houmao/agents/realm_controller/runtime.py`
  - `_resolve_manifest_path_from_tmux_session()`

This path explicitly resolves `AGENTSYS_MANIFEST_PATH` from tmux session env and validates it.

### 2. Repo-owned tmux env reading helpers already exist

- `src/houmao/agents/realm_controller/backends/tmux_runtime.py`
  - `read_tmux_session_environment_value()`

So the missing piece is not capability. It is consistent adoption.

### 3. Gateway runtime still uses process-env reads

- `src/houmao/agents/realm_controller/gateway_service.py`
  - `_optional_env_string()`
  - `GatewayServiceRuntime.__init__()`

Those paths currently read process env directly for runtime-owned fields.

### 4. Mailbox contract still presents env as process-local only

- `src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-filesystem/references/env-vars.md`
- `src/houmao/agents/realm_controller/assets/system_skills/mailbox/email-via-stalwart/references/env-vars.md`

They require `AGENTSYS_MAILBOX_*` bindings but do not document the tmux fallback rule that should exist under the tmux-container assumption.

## Desired Direction

The repo should make this contract explicit and uniform.

### 1. Standardize env resolution for runtime-owned vars

For runtime-owned env vars needed by managed agent, skill, gateway, or runtime workflows:

1. read from current process env first,
2. if missing and the session is tmux-backed, query the owning tmux session for that specific env var,
3. use that tmux value as the live runtime value,
4. only fail if neither source provides a valid value.

### 2. Keep lookup targeted, not broad

The system should query specific requested vars from the owning tmux session.

It should not require:

- dumping all tmux env,
- teaching the model to scrape tmux manually,
- or treating tmux as an unstructured second config store.

### 3. Hide tmux details behind runtime-owned helpers

Agent- or gateway-facing code should not duplicate tmux lookup logic inline.

The repo should expose runtime-owned helpers for targeted live env resolution so:

- mailbox flows,
- gateway flows,
- prompt builders,
- and future tmux-backed backends

can all use the same contract.

### 4. Preserve durable state separately

This issue does not argue for replacing manifests or other durable state with tmux env.

The intended split is:

- durable manifest/config = persistence and resume authority
- tmux session env = live mutable runtime projection
- process env = current process snapshot that may be incomplete or stale

## Acceptance Criteria

1. The repo has one explicit helper or contract for targeted runtime-owned env lookup with tmux fallback.
2. Gateway runtime paths that depend on runtime-owned env vars use that helper instead of assuming process env is complete.
3. Mailbox-related runtime and skill flows use the same helper or equivalent contract for `AGENTSYS_MAILBOX_*` lookup.
4. Docs state clearly that for tmux-backed managed sessions, missing runtime-owned env vars should be resolved from the owning tmux session before being treated as unavailable.
5. Tests cover the case where a runtime-owned env var is absent from the current process env but present in the owning tmux session env.

## Related Work

- [20260326-180258-mailbox-notifier-activation-contract-and-pid.md](/data1/huangzhe/code/houmao/context/logs/explore/20260326-180258-mailbox-notifier-activation-contract-and-pid.md)
- [issue-008-mailbox-prompt-should-not-reference-skill-install-paths.md](/data1/huangzhe/code/houmao/context/issues/known/issue-008-mailbox-prompt-should-not-reference-skill-install-paths.md)
- [use-tmux-live-mailbox-bindings](/data1/huangzhe/code/houmao/openspec/changes/use-tmux-live-mailbox-bindings)
