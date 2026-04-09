## Why

Headless agents already execute as one fresh CLI invocation per turn, but Houmao still treats model selection as primarily launch-owned state. That makes it awkward to switch model or reasoning level from one headless turn to the next even though the underlying runtime shape can support that flexibility.

We need a supported request-scoped override contract for headless prompt submission so operators can choose model and thinking level per turn without rewriting launch profiles, manifests, or other persistent runtime state.

## What Changes

- Add an optional request-scoped `execution.model` object to supported headless prompt submission surfaces.
- Reuse Houmao's normalized model-selection payload shape: `name` plus optional `reasoning.level` in the inclusive range `1..10`.
- Apply request overrides only to the addressed prompt submission; they do not mutate launch profiles, recipes, specialists, manifests, or other live session defaults.
- Extend managed headless turn submission and managed gateway prompt submission to accept the same override contract.
- Extend direct gateway prompt and queued gateway `submit_prompt` request payloads so immediate and queued gateway headless paths share one execution-override model.
- Extend `houmao-mgr agents turn submit`, `houmao-mgr agents gateway prompt`, and the transport-neutral `houmao-mgr agents prompt` path with `--model` and `--reasoning-level`.
- Reject execution overrides clearly when the resolved target is TUI-backed rather than silently ignoring them.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: extend direct and queued gateway prompt contracts with request-scoped headless execution overrides and define TUI rejection semantics.
- `agent-model-selection`: add request-scoped headless execution override precedence while keeping the override non-persistent and normalized.
- `houmao-server-agent-api`: extend managed headless turn and managed gateway prompt routes to accept and forward request-scoped execution overrides.
- `houmao-srv-ctrl-native-cli`: add `--model` and `--reasoning-level` to the supported headless prompt CLI surfaces and define rejection behavior for TUI targets.

## Impact

- Affected APIs: `POST /houmao/agents/{agent_ref}/turns`, `POST /houmao/agents/{agent_ref}/gateway/control/prompt`, `POST /houmao/agents/{agent_ref}/gateway/requests`, `POST /v1/control/prompt`, and `POST /v1/requests` for `submit_prompt`.
- Affected CLI: `houmao-mgr agents turn submit`, `houmao-mgr agents gateway prompt`, and `houmao-mgr agents prompt`.
- Affected runtime paths: gateway execution adapters, managed headless turn dispatch, and per-tool headless runtime projection for Codex, Claude, and Gemini.
- Non-goal: persistent live "current model" mutation for a running agent.
