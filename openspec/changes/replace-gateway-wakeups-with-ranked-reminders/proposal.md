## Why

The current gateway wakeup surface is built around independent one-off or repeating jobs. That model cannot express "only the highest-priority reminder is active", cannot block lower-priority reminders behind a paused higher-priority one, and does not provide first-class title and ranking fields for operator-visible reminder management.

We need to replace wakeups with a reminder model now because the desired behavior is not a small extension of the current contract. The public API, inspection state, skill guidance, and runtime arbitration rules all need to shift from isolated timer jobs to one ranked live reminder set.

## What Changes

- **BREAKING** Replace the live gateway wakeup route family `/v1/wakeups` with `/v1/reminders`.
- **BREAKING** Replace the current wakeup job model with live in-memory reminder records that include a title, prompt string, ranking, paused flag, and due-time scheduling fields.
- Add reminder-set arbitration where the reminder with the smallest ranking value is the only effective reminder and all other reminders remain pending behind it.
- Define that a paused effective reminder still keeps its ranking position and blocks lower-priority reminders, but does not submit prompts while paused.
- Preserve the existing readiness gate for prompt delivery: due reminder prompts are sent only when request admission is open, no terminal-mutating execution is active, and the durable public queue depth is zero.
- Allow callers to create more than one reminder in one request and inspect live effective-versus-blocked reminder state through the reminder HTTP surface.
- Update the packaged gateway skill and CLI reference docs to describe reminders instead of wakeups and to state the new ranking and pause behavior honestly.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway`: Replace ephemeral wakeup job requirements with ranked live reminder requirements, including rename to `/v1/reminders`, batch creation, effective-reminder arbitration, pause behavior, and updated inspection state.
- `houmao-agent-gateway-skill`: Replace wakeup guidance with reminder guidance and describe the live gateway reminder surface, ranking order, and pause semantics accurately.
- `docs-cli-reference`: Update CLI and system-skill reference requirements that currently describe direct live `/v1/wakeups` routes so they describe `/v1/reminders` instead.

## Impact

- Affected code: `src/houmao/agents/realm_controller/gateway_service.py`, `src/houmao/agents/realm_controller/gateway_models.py`, `src/houmao/agents/realm_controller/gateway_client.py`, gateway tests, and the packaged `houmao-agent-gateway` system skill assets.
- Affected API: direct live gateway HTTP callers must migrate from `/v1/wakeups` to `/v1/reminders`, and wakeup payloads and response models will be replaced by reminder models.
- Affected docs and skills: gateway contract docs, CLI/system-skill references, and gateway skill action pages will need to describe reminders as non-durable live gateway state.
