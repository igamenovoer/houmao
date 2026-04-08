# Issue: `cao_rest` Ignores Tool-Adapter `launch.args`

> Obsolete as of 2026-04-08.
> Moved from `context/issues/known/` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Priority
P1 — The runtime persists backend launch args that are not actually applied in CAO-backed sessions, which creates a misleading contract and can break hands-off automation assumptions.

## Status
Open as of 2026-03-18.

## Summary

Houmao tool adapters expose a generic `launch.args` field, and the brain builder persists those args into the brain manifest and launch plan for all backends.

That works for headless backends, but it does not work for `backend=cao_rest`.

For CAO-backed sessions, Houmao records `launch_plan.args`, yet the actual CAO terminal creation path does not forward those args into the live tool process. The final interactive command is assembled inside CAO from the selected provider and agent profile, not from Houmao's persisted `launch.args`.

The result is a backend-contract mismatch:

- config says one thing,
- session manifests repeat it,
- but the live CAO-backed tool process may run without those args.

## What Is Wrong Today

The current runtime treats `launch.args` as a backend-agnostic launch surface at build and manifest time, but `cao_rest` does not have a corresponding execution path for them.

This creates three concrete problems:

1. The same config field means different things on different backends.
2. `manifest.json` can imply that CAO-backed sessions were launched with args that never reached the real tool process.
3. Operators can spend time debugging the wrong layer because the persisted state looks authoritative even when CAO ignored it.

## Evidence

### 1. Tool-adapter args are persisted into the brain manifest

Houmao loads `launch.args` from tool adapters and writes them into the generated brain manifest:

- `src/houmao/agents/brain_builder.py`

Relevant flow:

- `_load_tool_adapter()` reads `launch.args`
- `build_brain_home()` persists `launch_args` into the brain manifest payload

### 2. Launch-plan construction carries those args into `LaunchPlan.args`

The realm-controller launch-plan layer copies brain-manifest `launch_args` into the resolved launch plan:

- `src/houmao/agents/realm_controller/launch_plan.py`

For `backend=cao_rest`, there is no special transformation that makes those args executable through CAO. They are simply retained in `LaunchPlan.args`.

### 3. The `cao_rest` start path does not forward `LaunchPlan.args`

When a CAO-backed session starts, `CaoRestSession._start_terminal()` calls the CAO REST client with only:

- `provider`
- `agent_profile`
- `working_directory`

Source:

- `src/houmao/agents/realm_controller/backends/cao_rest.py`
- `src/houmao/cao/rest_client.py`

There is no argument field in this call path for generic per-session CLI args.

### 4. The CAO REST API surface does not expose generic launch args either

CAO's REST and service layers accept:

- `provider`
- `agent_profile`
- `session_name`
- `working_directory`

Sources:

- `extern/tracked/cli-agent-orchestrator/src/cli_agent_orchestrator/api/main.py`
- `extern/tracked/cli-agent-orchestrator/src/cli_agent_orchestrator/services/terminal_service.py`

There is no CAO API field for arbitrary extra CLI args to be forwarded to the provider launch command.

### 5. CAO providers build their own commands internally

For example, the Codex provider constructs its own command in `_build_codex_command()` and starts from provider-owned defaults:

- `extern/tracked/cli-agent-orchestrator/src/cli_agent_orchestrator/providers/codex.py`

Likewise, the Claude provider builds its own command in `_build_claude_command()`:

- `extern/tracked/cli-agent-orchestrator/src/cli_agent_orchestrator/providers/claude_code.py`

Those command builders do not consume Houmao's tool-adapter `launch.args`.

### 6. Real reproduction: persisted args did not match the live Codex command

During the 2026-03-18 HTT run for the skill-invocation demo pack, a Codex CAO-backed session manifest showed a configured bypass flag under `launch_plan.args`, but the live tmux pane still launched plain:

```text
codex --no-alt-screen --disable shell_snapshot ...
```

instead of including the configured extra flag.

That reproduction confirmed the contract gap in a real CAO-backed session, not just by source inspection.

## Root Cause

The core design mismatch is this:

1. Houmao models tool launch args as part of a generic launch plan.
2. `cao_rest` does not actually own the final provider command line.
3. CAO owns the final provider command line, but its terminal-creation API does not accept generic extra args from Houmao.

So `launch.args` currently behaves like a headless/backend-local concept that is being serialized as though it were universal.

## Impact

- CAO-backed session manifests can overstate what was actually launched.
- Maintainers can make seemingly reasonable config changes that have no effect on live CAO-backed tools.
- Debugging becomes slower because the failure looks like a provider bug, a trust bug, or an operator mistake before the boundary mismatch is noticed.
- Backends stop feeling interchangeable even though the shared config surface suggests they are.

## Current Workaround

Do not rely on tool-adapter `launch.args` to change live CAO-backed tool behavior.

For Codex approval and sandbox posture, the supported workaround is to use the selected Codex config profile and let Houmao's runtime bootstrap project those settings into the generated `CODEX_HOME/config.toml`.

Related troubleshooting note:

- `docs/reference/agents/troubleshoot/codex-cao-approval-prompt-troubleshooting.md`

That workaround is specific to config-backed Codex behavior. It does not solve the general `launch.args` contract gap for `cao_rest`.

## Desired Direction

One of these directions should be chosen explicitly.

### Option 1: Make `launch.args` non-applicable to `cao_rest`

If Houmao intends CAO-backed sessions to be provider-profile-driven rather than tool-adapter-arg-driven, then the runtime should:

- fail fast when `launch.args` is non-empty for `backend=cao_rest`, or
- omit those args from the CAO launch-plan/session contract and document the limitation clearly.

This is the simplest direction if we want a clean boundary.

### Option 2: Extend the CAO boundary so args can really flow through

If Houmao wants `launch.args` to be meaningful for CAO-backed sessions, then the boundary must be extended so those args actually reach the provider command builder.

That likely means changes across:

- Houmao's `cao_rest` boundary,
- Houmao's CAO REST client,
- CAO's terminal-creation API,
- and provider launch-command assembly.

Without that end-to-end support, persisting `launch.args` for `cao_rest` remains misleading.

## Acceptance Criteria

1. The repo documents whether `launch.args` is supported for `backend=cao_rest`.
2. CAO-backed session manifests no longer imply support that the runtime cannot deliver.
3. Either:
   - `cao_rest` rejects non-empty `launch.args`, or
   - CAO-backed sessions truly pass those args through to the final tool process.
4. A real CAO-backed test demonstrates the chosen contract.

## Connections

- Related to `docs/reference/agents/troubleshoot/codex-cao-approval-prompt-troubleshooting.md`
- Related to `context/issues/resolved/issue-codex-model-migration-modal-blocks-interactive-demo-startup.md`
