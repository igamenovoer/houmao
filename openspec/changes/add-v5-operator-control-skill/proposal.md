## Why

Generated loops currently rely on generic v5 execution operations for lifecycle control, so operators must repeatedly identify which loop they mean and infer loop-local control details from the execplan. A generated loop-local operator control skill gives each loop a stable control surface for lifecycle operations, auto/manual mode, and recovery posture without inventing a global loop identity system.

## What Changes

- Require generated execplans with lifecycle control needs to emit a loop-bound `<loop-slug>-operator-control` skill under the flat `execplan/skills/` namespace.
- Define operator-control coverage for loop lifecycle operations such as status, start, pause, resume, stop, recover, and manual stepping.
- Add generated harness control surfaces for run state, execution mode, operator intent events, and mode-aware participant context.
- Define `auto` versus `manual` execution mode semantics:
  - `auto`: mail notifier prompts remain the normal wakeup path.
  - `manual`: mail notification is suspended and the operator drives bounded participant work through prompts.
- Require generated on-tick skills to query execution mode and branch between auto-mode and manual-mode bounded behavior.
- Update generated agent binding and notifier prompt guidance so auto mode uses notifier-driven mail turns while manual mode uses operator-prompted turns.
- Update validation guidance to check operator-control skill generation, mode query surfaces, mode switching boundaries, and no in-chat waiting posture.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: Add default generated operator-control skill guidance, loop execution mode contracts, harness mode query commands, mode-aware on-tick behavior, and validation expectations.

## Impact

Affected assets are limited to `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`, its developer design notes, and the OpenSpec documentation for the existing v5 skill capability. No Houmao runtime CLI, mailbox transport, gateway API, workspace manager, or managed-agent launch API behavior is intended to change; generated operator-control must route platform mechanics through maintained Houmao skills.
