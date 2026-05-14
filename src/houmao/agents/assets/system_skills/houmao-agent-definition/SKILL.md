---
name: houmao-agent-definition
description: Use Houmao's canonical pre-launch agent-definition skill to create, inspect, update, or remove low-level roles and recipes, explicit launch profiles, project-easy specialists, easy profiles, ready-to-launch easy profiles, and limited easy launch or stop entry points.
license: MIT
---

# Houmao Agent Definition

Use this Houmao skill when the task is about persisted pre-launch agent definitions: what an agent is, which reusable profile should launch it, and which launch defaults should be stored before runtime.

The trigger word `houmao` is intentional. Use the `houmao-agent-definition` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This skill is the canonical router for:

- low-level roles: `houmao-mgr project agents roles ...`
- low-level recipes: `houmao-mgr project agents recipes ...`
- compatibility recipe aliases: `houmao-mgr project agents presets ...`
- explicit recipe-backed launch profiles: `houmao-mgr project agents launch-profiles ...`
- project-easy specialists: `houmao-mgr project easy specialist ...`
- specialist-backed easy profiles: `houmao-mgr project easy profile ...`
- ready easy-profile generation: create or select a specialist, create or update an easy profile, print the launch command, and do not launch
- limited easy launch and stop entry points: `houmao-mgr project easy instance launch|stop`, followed by handoff to `houmao-agent-instance` for broader live lifecycle work

This skill does not own:

- credential bundle CRUD or secret mutation: use `houmao-credential-mgr`
- mailbox root/account administration: use `houmao-mailbox-mgr`
- workspace creation: use `houmao-utils-workspace-mgr`
- broad live managed-agent lifecycle after launch: use `houmao-agent-instance`
- direct hand-editing under `.houmao/`

## Workflow

1. Identify the lane:
   - role
   - recipe or preset
   - explicit recipe-backed launch profile
   - easy specialist
   - easy profile
   - ready profile
   - easy launch
   - easy stop
2. Read the shared pages needed by that lane:
   - [subskills/common/launcher.md](subskills/common/launcher.md)
   - [subskills/common/missing-inputs.md](subskills/common/missing-inputs.md)
   - [subskills/common/profile-lanes.md](subskills/common/profile-lanes.md) when a profile lane is involved
   - [subskills/common/credential-routing.md](subskills/common/credential-routing.md) when credentials or auth names are involved
3. Load exactly one lane subskill:
   - [subskills/low-level/roles.md](subskills/low-level/roles.md)
   - [subskills/low-level/recipes.md](subskills/low-level/recipes.md)
   - [subskills/low-level/launch-profiles.md](subskills/low-level/launch-profiles.md)
   - [subskills/easy/specialists.md](subskills/easy/specialists.md)
   - [subskills/easy/profiles.md](subskills/easy/profiles.md)
   - [subskills/easy/create-ready-agent-profile.md](subskills/easy/create-ready-agent-profile.md)
   - [subskills/easy/launch-instance.md](subskills/easy/launch-instance.md)
   - [subskills/easy/stop-instance.md](subskills/easy/stop-instance.md)
4. Resolve one `houmao-mgr` launcher and reuse it for the turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if those do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request
5. Run the selected maintained command only after all required inputs are explicit.
6. Report command output and any durable identity facts that affect later launch.

## Routing Rules

- Use low-level role guidance for prompt-only role resources.
- Use low-level recipe guidance for reusable build-phase bundles of role, tool, setup, auth reference, skills, and prompt mode.
- Use explicit launch-profile guidance for recipe-backed birth-time defaults under `project agents launch-profiles ...`.
- Use easy specialist guidance for reusable specialist templates under `project easy specialist ...`.
- Use easy profile guidance for specialist-backed birth-time defaults under `project easy profile ...`.
- Use ready-profile guidance when the user wants one ready-to-launch easy profile prepared in one pass.
- Use easy launch or stop guidance only for the project-easy entry points, then hand off broad live-agent lifecycle to `houmao-agent-instance`.

## Guardrails

- Do not guess between low-level and easy lanes.
- Do not guess between easy profiles and explicit launch profiles; both project into launch-profile files, but the management lanes are distinct.
- Do not remove and recreate a role, recipe, specialist, or profile for ordinary patch edits when a maintained `set` command exists.
- Do not mutate credential bundle contents through this skill; route secret and auth-file edits to `houmao-credential-mgr`.
- Do not preregister same-root ordinary per-agent mailbox addresses as the default precursor to mailbox-enabled easy launch; profile defaults or launch-time easy bootstrap can own that common case.
- Do not use retired `houmao-mgr project agents roles scaffold`.
- Do not use retired `houmao-mgr project agents roles presets ...`.
- Do not use deprecated `houmao-cli` or removed standalone CAO launcher workflows.
