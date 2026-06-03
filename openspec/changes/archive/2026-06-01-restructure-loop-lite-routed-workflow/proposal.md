## Why

`houmao-agent-loop-lite` currently carries most of its authoring and execution guidance in a single `SKILL.md`, which makes it feel like a shortcut skill rather than a simplified version of the pro loop workflow. Lite should keep the same routed operating shape as `houmao-agent-loop-pro` while simplifying only the generated artifact model: Markdown contracts, typed Markdown templates, generated skills, and direct SQLite state instead of JSON schemas, Jinja2, and harness commands.

## What Changes

- Restructure the packaged `houmao-agent-loop-lite` skill so `SKILL.md` becomes an entrypoint/router with help, operations, routing, root vocabulary, and global constraints.
- Add lite `subskills/authoring/`, `subskills/execution/`, and `subskills/reference/` pages mirroring the pro lifecycle stages where applicable.
- Add lite scaffold support under `assets/scaffolds/` and `scripts/scaffold.py` for intention material and Markdown/direct-SQL execplan shells.
- Preserve lite-specific generated artifacts: Markdown manifest/specs, typed Markdown communication templates, generated skills, agent bindings, optional workspace/profile/notifier material, and direct SQLite state under runs.
- Keep heavy pro-only layers out of lite: no JSON schemas, no Jinja2 renderers, no generated harness, and no generated docs layer.
- Update packaged-skill tests and docs guards so the routed lite shape is installed and remains distinct from pro.
- **BREAKING**: Treat the existing single-page lite skill layout as non-conforming; lite operation details move into routed subskill pages.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-lite-skill`: require the packaged lite skill to use the same router/subskill/scaffold organization pattern as pro while retaining Markdown/direct-SQL/no-harness generated artifacts.

## Impact

- Affected assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-lite/`.
- Affected tests: packaged system-skill asset tests, installation projection tests, and documentation guards.
- Affected docs: loop authoring and system-skill overview docs may need wording updates to emphasize that lite is pro-shaped in workflow and lite only in generated artifact mechanisms.
- No runtime dependency changes are expected; the change is primarily system-skill packaging, guidance, scaffolding, and validation coverage.
