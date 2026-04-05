## Why

Houmao currently ships only mailbox-oriented Houmao-owned system skills, so agents do not have a built-in Houmao-owned skill for creating reusable easy specialists through the supported `houmao-mgr project easy specialist create` workflow. Adding that skill also exposes a packaging gap: the system-skill installer needs a flat tool-native top-level path contract so non-mailbox Houmao skills do not inherit a mailbox-specific visible layout.

## What Changes

- Add one packaged Houmao-owned system skill named `houmao-create-specialist` under `src/houmao/agents/assets/system_skills/`.
- Define the skill contract around `houmao-mgr project easy specialist create`, including launcher selection for end-user and development-project environments, recent-context recovery for omitted inputs, and explicit ask-before-guess behavior for unresolved required inputs.
- Keep system-skill projection flat and tool-native so Claude, Codex, and Gemini all install Houmao-owned skills as top-level skill directories under their active skill root.
- Add a named system-skill set for the project-easy authoring skill and include it in the default managed-launch, managed-join, and CLI-default auto-install selections.
- Add or update tests covering catalog selection, flat projection, and the installed `houmao-create-specialist` skill content.

## Capabilities

### New Capabilities
- `houmao-create-specialist-skill`: Provide a Houmao-owned skill that guides agents to create easy specialists through `houmao-mgr project easy specialist create` without guessing missing required inputs.
- `houmao-system-skill-families`: Package and project Houmao-owned system skills through flat tool-native top-level paths rather than through visible family-specific namespaces.

### Modified Capabilities

## Impact

- Affected code includes `src/houmao/agents/system_skills.py`, the packaged system-skill catalog and assets, and mailbox/runtime helpers that report projected skill references.
- Affected tests include system-skill catalog and projection coverage plus managed-home content assertions.
- Affected user-facing content includes the installed Houmao-owned skill inventory and any docs that still describe the system-skill surface as mailbox-only.
