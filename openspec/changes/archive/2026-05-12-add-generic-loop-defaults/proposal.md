## Why

The pairwise loop skill already separates editable intention source from generated execution material, but its default generation guidance does not yet capture the reusable workspace, execplan, harness, state, and event-skill patterns found in mature loop runs. Adding concise generic defaults reduces user effort while keeping task-specific behavior in intention and generated per-loop contracts.

## What Changes

- Add default guidance for generating flexible loop scaffolds that include workspace contracts, execplan manifests, participant registries, communication registries, minimal runtime state, harness surfaces, event skills, and run audit directories.
- Keep these defaults generic: task objectives, participant topology, policies, evidence rules, and domain records continue to come from intention source or explicit clarification.
- Document the boundary between defaults, generated loop contracts, maintained Houmao operation skills, and task-specific generated behavior.
- Reuse existing mail-default requirements rather than redefining Houmao mail transport behavior inside this change.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: Add generic default execplan and runtime scaffold expectations for generated loops.

## Impact

Affected assets are limited to `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/` and its developer design documentation. No runtime Python API, CLI command, or mailbox transport behavior is intended to change.
