## Why

The current v5 execution model allows `prepare-agents` to defer live launch until workspace and readiness facts exist, but no later stage clearly owns the actual launch transition before loop start. This makes `start` ambiguous: it both checks whether agents are live or launchable and sends the first loop trigger.

## What Changes

- Add `launch-agents` as a separate v5 execution subcommand.
- Revise the normal execution workflow to:
  - `prepare-agents`
  - `prepare-workspace` when managed workspace setup is needed, or manual workspace setup with equivalent readiness facts
  - `validate-loop`
  - `launch-agents`
  - `start`
- Revise `prepare-agents` so it prepares concrete launch profiles and launch facts, but does not launch live agents as normal behavior.
- Revise `validate-loop` so it validates launchability and loop readiness before launch, while accepting either `prepare-workspace` output or equivalent manual workspace evidence.
- Add `launch-agents` guidance that launches prepared agents through maintained Houmao launch surfaces and reports live-agent/session facts without sending loop-start work.
- Revise `start` so it requires launched/live agents and only sends the generated first loop trigger.
- Keep `validate-execplan` scoped to generated artifact shape, including stage-order checks for the new `launch-agents` stage.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: Execution-stage behavior changes to separate live agent launch from loop start and introduce `launch-agents` between `validate-loop` and `start`.

## Impact

- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`.
- Affected execution routing: add `launch-agents`; update execution order guidance.
- Affected execution pages: revise `prepare-agents`, `prepare-workspace`, `validate-loop`, and `start`; add `launch-agents`.
- Affected validation guidance: update `validate-execplan` and generated defaults to expect `prepare-agents`, optional/equivalent workspace readiness, `validate-loop`, `launch-agents`, then `start`.
- Affected developer design docs: clarify that launch is a distinct runtime transition, not profile preparation and not loop begin.
