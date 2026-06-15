## Why

The graphing skill was introduced as `houmao-utils-graphing`, but its behavior is closer to an optional extension than a general utility: it adds a focused authoring workflow on top of AG-UI rather than supporting core agent operation. Keeping it in `core` also forces non-extension skills such as `houmao-interop-ag-ui` to route users toward a skill they may choose to ignore or disable.

## What Changes

- **BREAKING**: Rename the packaged graphing skill from `houmao-utils-graphing` to `houmao-ext-graphing`.
- Treat graphing as part of an `extensions` category and installable named set instead of the `utils` group.
- Install extension skills by default alongside core skills for managed launch and managed join homes, while preserving `all` as the CLI-default umbrella set.
- Remove non-extension-to-extension routing: core and other non-extension skills must not tell agents to use `houmao-ext-graphing` as a required handoff or delegated workflow.
- Retire the old `houmao-utils-graphing` projection name so install, sync, and uninstall flows clean up stale copied or symlinked assets.
- Update system-skill docs and tests so operators see graphing as default-installed but optional extension guidance.

## Capabilities

### New Capabilities

- `houmao-ext-graphing-skill`: Defines the new `houmao-ext-graphing` extension system skill for built-in Plotly.js templated graphics and Vega-Lite freeform graphics authoring over Houmao AG-UI implementation schemas.

### Modified Capabilities

- `houmao-interop-ag-ui-skill`: Keep AG-UI interop focused on protocol, implementation rendering, publishing, and delivery interpretation without routing agents to the graphing extension.
- `houmao-mgr-system-skills-cli`: Surface `houmao-ext-graphing`, retire `houmao-utils-graphing`, add the `extensions` set, and report default auto-install set lists that include extensions.
- `houmao-system-skill-families`: Define extension skills as a distinct logical category and installable set, while keeping flat tool-native projection.
- `docs-system-skills-overview-guide`: Document the extension category, the graphing skill rename, and the rule that non-extension skills do not depend on extension skills.
- `docs-cli-reference`: Document the current `extensions` named set and default install behavior in the system-skills CLI reference.

## Impact

- System skill assets under `src/houmao/agents/assets/system_skills/`, including the graphing asset directory and `houmao-interop-ag-ui` skill text.
- Packaged system-skill catalog constants, catalog TOML, set resolution, default auto-install reporting, and retired-skill cleanup.
- Unit tests for packaged system-skill catalog contracts, CLI list/install/status/uninstall behavior, docs coverage, and default managed skill selection.
- Documentation under `docs/getting-started/system-skills-overview.md` and `docs/reference/cli/system-skills.md`.
