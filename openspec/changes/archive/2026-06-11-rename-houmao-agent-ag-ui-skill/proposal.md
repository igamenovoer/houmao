## Why

The packaged AG-UI authoring skill is currently named `houmao-agent-ag-ui`, which is narrower than its actual role as the agent-facing bridge between Houmao typed components, AG-UI events, gateway publishing, and GUI/workbench behavior. Renaming it to `houmao-interop-ag-ui` gives the skill a clearer long-term identity before more AG-UI interop surfaces are added.

## What Changes

- **BREAKING** Rename the packaged system skill from `houmao-agent-ag-ui` to `houmao-interop-ag-ui` across the catalog key, asset directory, installed projection directory, skill frontmatter, help prompts, constants, docs, tests, and current OpenSpec capability name.
- Add `houmao-agent-ag-ui` to the known retired system-skill names so install and sync flows remove stale old-name projections from existing tool homes.
- Keep the skill's AG-UI authoring, schema discovery, validation, event rendering, gateway publishing, active-thread fallback, and safety guidance behavior intact under the new name.
- Update the active `add-ag-ui-template-graphics-vega` change artifacts that still refer to the old skill name.
- Leave AG-UI protocol routes, workbench route names, `houmao-mgr internals ag-ui`, and gateway publish command names unchanged.
- Leave archived OpenSpec changes as historical records unless a separate archival rewrite is requested.

## Capabilities

### New Capabilities

- `houmao-interop-ag-ui-skill`: Maintained renamed system skill that teaches Houmao agents how to generate, validate, render, publish, and reason about UI-facing AG-UI/Houmao component messages.

### Modified Capabilities

- `houmao-agent-ag-ui-skill`: Old-name skill capability is removed in favor of `houmao-interop-ag-ui-skill`.
- `houmao-system-skill-installation`: Current packaged system-skill inventory uses `houmao-interop-ag-ui`, and retired-skill cleanup recognizes `houmao-agent-ag-ui`.
- `houmao-mgr-system-skills-cli`: `system-skills list`, `install`, and `status` report and project the new skill name rather than the old name.
- `docs-system-skills-overview-guide`: The narrative system-skills guide lists `houmao-interop-ag-ui` as the current AG-UI interop skill and does not list `houmao-agent-ag-ui` as current.

## Impact

- Packaged system-skill assets under `src/houmao/agents/assets/system_skills/`.
- System-skill catalog loading, constants, selection, install, sync, status, and retired cleanup behavior in `src/houmao/agents/system_skills.py`.
- Managed home construction and explicit `houmao-mgr system-skills` tests that assert installed skill names and projected paths.
- Current OpenSpec specs and the active AG-UI template graphics change artifacts that mention the old skill name.
- Documentation that enumerates current packaged system skills.
