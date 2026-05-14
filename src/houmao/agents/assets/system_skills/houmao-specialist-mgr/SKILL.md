---
name: houmao-specialist-mgr
description: Compatibility wrapper. Route specialist, easy-profile, ready-profile, and easy launch or stop work to the canonical `houmao-agent-definition` skill.
license: MIT
---

# Houmao Specialist Manager Compatibility Wrapper

`houmao-specialist-mgr` is retained only as a compatibility entry point for older prompts and installed homes.

## Current Owner

Use `houmao-agent-definition` for current specialist and profile work:

- easy specialists: `houmao-agent-definition/subskills/easy/specialists.md`
- easy profiles: `houmao-agent-definition/subskills/easy/profiles.md`
- ready-to-launch easy profiles: `houmao-agent-definition/subskills/easy/create-ready-agent-profile.md`
- easy launch: `houmao-agent-definition/subskills/easy/launch-instance.md`
- easy stop: `houmao-agent-definition/subskills/easy/stop-instance.md`
- credential discovery used during specialist creation: `houmao-agent-definition/references/credentials/`

## Workflow

1. Tell the user or calling agent that `houmao-agent-definition` is the canonical skill.
2. Switch to the matching `houmao-agent-definition` subskill.
3. Do not run commands from this wrapper.
4. Do not maintain separate specialist, profile, launch, stop, or credential-reference guidance here.

## Guardrails

- Do not present this skill as the independent owner for specialist or easy-profile workflows.
- Do not duplicate command details from `houmao-agent-definition`.
- Do not route broad live-agent lifecycle work here; use `houmao-agent-instance` after any easy launch or stop.
