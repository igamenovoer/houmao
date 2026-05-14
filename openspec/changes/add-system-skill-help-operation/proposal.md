## Why

Houmao system skills are installed as agent-facing instruction packages, but the first thing an agent or operator often needs is a compact explanation of what a selected skill can do before starting a mutating workflow. A standard `help` meta operation across all current system skills will make installed skills self-describing, especially when users install skills individually through external skill tooling.

## What Changes

- Add a standard `help` meta operation to every current packaged Houmao system skill.
- Make `help` a read-only response path: it explains the skill purpose, available functionality, common starting prompts, and related skill boundaries without running commands or mutating Houmao state.
- Require each current skill's top-level `SKILL.md` to recognize explicit help intent such as `<skill-name> help`, `usage`, `available functionality`, or "what can this skill do?"
- Require operation-heavy skills to list `help` beside their operations and to route it before any normal operation such as `init`, `status`, `send`, or `launch`.
- Require router-style skills to handle help before selecting action pages, branches, transport pages, or reference material.
- Keep the help content local to each installed skill so individually installed skills remain self-contained.
- Keep help trigger boundaries narrow so "help me do X" continues into the actual workflow, while "help for this skill" produces a usage response.
- Update README and system-skills overview guidance so users know they can ask any installed Houmao system skill for help.
- Add tests that verify all current catalog skills expose the standard help contract and that legacy retired skills are not required to adopt it.

## Capabilities

### New Capabilities

- `houmao-system-skill-help-operation`: Cross-cutting contract for a standard read-only `help` meta operation in every current packaged Houmao system skill.

### Modified Capabilities

- `docs-readme-system-skills`: README system-skill guidance mentions the standard help operation for installed skills.
- `docs-system-skills-overview-guide`: System-skills overview explains that each current skill can answer help/usage requests before normal workflow routing.

## Impact

- Affected skill assets: all current top-level `src/houmao/agents/assets/system_skills/<current-skill>/SKILL.md` files declared in `catalog.toml`.
- Out of scope: retired legacy skill source trees under `src/houmao/agents/assets/system_skills/legacy/`.
- Affected docs: README and system-skills overview.
- Affected tests: system-skill catalog/content tests and docs guard tests.
- No runtime API, CLI command, catalog schema, or data migration is required.
