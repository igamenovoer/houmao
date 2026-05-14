---
name: houmao-specialist-mgr
description: Compatibility wrapper. Route specialist, profile, create-agent-fast-forward, launch-agent, and stop-agent work to the canonical `houmao-agent-definition` skill.
license: MIT
---

# Houmao Specialist Manager Compatibility Wrapper

`houmao-specialist-mgr` is retained only as a compatibility entry point for older prompts and installed homes.

## Help

When the user asks `$houmao-specialist-mgr help`, `help for houmao-specialist-mgr`, `usage for houmao-specialist-mgr`, `available functionality for houmao-specialist-mgr`, or what this skill can do, answer from this section before switching to another subskill or workflow. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me create a specialist", explain the compatibility handoff and route to `houmao-agent-definition` instead of stopping at generic help.

Purpose: keep older specialist/profile prompts working by redirecting them to the canonical `houmao-agent-definition` skill.

Available functionality:

- Explain that this wrapper has no independent command ownership.
- Redirect specialist, profile, create-agent-fast-forward, launch-agent, and stop-agent work to `houmao-agent-definition`.
- Preserve older ready-profile wording as compatibility terminology.
- Point credential discovery used during specialist creation to the canonical definition skill.

Common starting prompts:

- `$houmao-specialist-mgr help`
- `$houmao-specialist-mgr create a specialist`
- `$houmao-specialist-mgr create-agent-fast-forward`
- `$houmao-specialist-mgr launch-agent`

Related skills and boundaries:

- Use `houmao-agent-definition` for current specialist, profile, easy launch, easy stop, and credential-reference workflows.
- Use `houmao-agent-instance` for broad live-agent lifecycle after launch or stop.
- Do not maintain separate command details in this wrapper.

## Current Owner

Use `houmao-agent-definition` for current specialist and profile work:

- `specialists`: `houmao-agent-definition/subskills/easy/specialists.md`
- `profiles`: `houmao-agent-definition/subskills/easy/profiles.md`
- `create-agent-fast-forward`: `houmao-agent-definition/subskills/easy/create-agent-fast-forward.md`
- `launch-agent`: `houmao-agent-definition/subskills/easy/launch-instance.md`
- `stop-agent`: `houmao-agent-definition/subskills/easy/stop-instance.md`
- credential discovery used during specialist creation: `houmao-agent-definition/references/credentials/`

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Tell the user or calling agent that `houmao-agent-definition` is the canonical skill.
2. Switch to the matching `houmao-agent-definition` subskill.
3. Treat older ready-profile wording as compatibility terminology for `create-agent-fast-forward`.
4. Do not run commands from this wrapper.
5. Do not maintain separate specialist, profile, launch, stop, or credential-reference guidance here.

## Guardrails

- Do not present this skill as the independent owner for specialist or easy-profile workflows.
- Do not duplicate command details from `houmao-agent-definition`.
- Do not route broad live-agent lifecycle work here; use `houmao-agent-instance` after any easy launch or stop.
