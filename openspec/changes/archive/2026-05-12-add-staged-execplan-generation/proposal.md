## Why

Execplan generation currently describes the package layers but not the order in which those layers should be produced. A staged generation workflow will make the process model the first generated authority, then derive contracts, harness, skills, agent bindings, and final package views in a dependency-safe order.

## What Changes

- Add staged execplan authoring subcommands:
  - `execplan-specs-process`
  - `execplan-specs-contract`
  - `execplan-harness`
  - `execplan-skills`
  - `execplan-agent-bindings`
  - `execplan-finalize`
- Make `generate-execplan` the orchestration command that runs those stages in order.
- Make `update-execplan` rerun the appropriate stage range after intention changes.
- Document that `execplan-specs-process` is the first generated stage and that objective, participants, comms, state, workspace, harness, skills, agents, docs, and manifest finalization are derived from it.
- Keep the stages generic and optional-aware; simple loops may omit irrelevant artifacts when omissions are explicit.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: Add staged execplan generation subcommands and dependency-order guidance.

## Impact

Affected assets are limited to `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`, its `agents/openai.yaml`, developer design notes, and OpenSpec documentation for the existing skill capability. No Houmao runtime CLI, mailbox transport, workspace manager, or managed-agent API behavior is intended to change.
