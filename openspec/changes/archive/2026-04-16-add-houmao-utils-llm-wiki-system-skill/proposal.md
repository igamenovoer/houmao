## Why

Houmao now tracks the all-in-one LLM Wiki skill source, but users cannot install it through Houmao's packaged system-skill surface. Adding it as a Houmao utility skill makes the persistent Markdown knowledge-base workflow available through the same `houmao-mgr system-skills` catalog and projection machinery as the rest of Houmao's agent-facing skills.

## What Changes

- Add a packaged Houmao-owned system skill named `houmao-utils-llm-wiki`.
- Adapt the all-in-one LLM Wiki skill text for Houmao packaging while preserving the wiki workflow, scripts, references, subskills, and bundled viewer payload.
- Add a new `utils` named set containing `houmao-utils-llm-wiki`.
- Keep the `utils` set explicit-only: do not add it to `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets`.
- Document installation through `--skill-set utils` and direct `--skill houmao-utils-llm-wiki`.
- Use `python3` in helper script examples.
- Do not preserve upstream attribution text in the packaged Houmao system skill.

## Capabilities

### New Capabilities

### Modified Capabilities
- `houmao-system-skill-installation`: Add the utility skill to the packaged catalog contract and define its explicit-only selection behavior.
- `houmao-system-skill-flat-layout`: Require the new utility skill to remain in the flat packaged asset and tool-visible projection layout.
- `houmao-system-skill-families`: Add the utility logical group without changing projection-family semantics.
- `houmao-mgr-system-skills-cli`: Surface the new skill and `utils` set through list, install, status, and uninstall behavior.
- `docs-readme-system-skills`: Document the new packaged utility skill and explicit install examples in the README system-skills table.
- `docs-system-skills-overview-guide`: Add the new utility skill to the narrative system-skills guide and default-selection explanation.
- `docs-cli-reference`: Add CLI reference coverage for the new skill, named set, and explicit-only default behavior.

## Impact

- Adds a new packaged asset tree under `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/`.
- Updates `src/houmao/agents/assets/system_skills/catalog.toml`.
- Updates system-skill catalog tests and CLI tests that enumerate current skills, sets, and default selections.
- Updates README and system-skills documentation where the current catalog inventory and named sets are listed.
- Increases packaged asset size because the full all-in-one payload includes scripts and the local web viewer source.
- Does not change managed launch/join auto-install defaults or the CLI-default install selection.
