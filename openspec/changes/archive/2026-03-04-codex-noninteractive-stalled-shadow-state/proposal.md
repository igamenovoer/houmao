## Why

Codex CAO-backed launches can still hit interactive trust/onboarding prompts when runtime-generated homes do not proactively seed non-interactive `config.toml` state. In parallel, shadow parsing can remain in unclassifiable output patterns long enough to look like a hang, with no first-class stalled state to explain what happened.

## What Changes

- Add runtime Codex home bootstrap logic that updates generated `config.toml` at launch time to reduce interactive prompts in orchestrated sessions.
- Move per-workdir trust seeding from ad hoc demo behavior into runtime-owned launch behavior (with explicit, documented policy).
- Extend shadow parser status modeling with `unknown` and runtime-derived `stalled` behavior when unknown output persists beyond a configurable timeout.
- Make stalled behavior configurable as terminal or non-terminal:
  - terminal: fail turn immediately when `stalled` is reached,
  - non-terminal: keep periodic polling and allow recovery back to known states.
- Enrich runtime diagnostics/metadata so users can see unknown/stalled timing and recovery context.
- Add/update troubleshooting documentation in `docs/reference` for non-interactive Codex bootstrap and unknown/stalled shadow parsing behavior.

## Capabilities

### New Capabilities

- *(none)*

### Modified Capabilities

- `brain-launch-runtime`: CAO/runtime launch behavior adds Codex non-interactive bootstrap and configurable unknown->stalled runtime policy.
- `cao-codex-output-extraction`: Codex shadow status semantics add `unknown`/`stalled` lifecycle and stalled recovery handling.
- `cao-claude-code-output-extraction`: Claude shadow status semantics add `unknown`/`stalled` lifecycle and stalled recovery handling.

## Impact

- Runtime launch/backends:
  - `src/agent_system_dissect/agents/brain_launch_runtime/backends/cao_rest.py`
  - `src/agent_system_dissect/agents/brain_launch_runtime/backends/codex_app_server.py`
  - new/updated Codex bootstrap helper(s) for runtime home config materialization.
- Shadow parser core/contracts:
  - `src/agent_system_dissect/agents/brain_launch_runtime/backends/shadow_parser_core.py`
  - provider parsers and stack adapters for status propagation.
- Config and builder surfaces:
  - Codex config profile defaults and/or runtime overlay logic for generated homes.
- Tests:
  - unit tests for bootstrap config projection and unknown->stalled transition/recovery behavior.
- Docs:
  - `docs/reference/cao_shadow_parser_troubleshooting.md`
  - `docs/reference/brain_launch_runtime.md`
