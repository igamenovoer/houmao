## ADDED Requirements

### Requirement: Packaged catalog uses the renamed AG-UI interop skill
The packaged current-system-skill catalog SHALL include `houmao-interop-ag-ui` as a current installable Houmao-owned system skill.

That packaged skill SHALL use `houmao-interop-ag-ui` as both its catalog key and packaged `asset_subpath`.

The packaged catalog's `core` and `all` named sets SHALL include `houmao-interop-ag-ui` wherever the old AG-UI authoring skill was previously included.

The packaged current-system-skill catalog SHALL NOT include `houmao-agent-ag-ui` as a current installable skill.

The packaged catalog SHALL list `houmao-agent-ag-ui` as a known retired skill name so install and sync flows remove stale old-name projections from target tool homes.

#### Scenario: Catalog exposes the renamed AG-UI interop skill
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-interop-ag-ui`
- **AND THEN** the `core` and `all` sets resolve `houmao-interop-ag-ui`
- **AND THEN** the current installable skill inventory does not include `houmao-agent-ag-ui`

#### Scenario: Installer removes stale old-name projection
- **WHEN** a target Codex home contains `skills/houmao-agent-ag-ui`
- **AND WHEN** Houmao installs or syncs the current system-skill selection for that home
- **THEN** the operation removes the stale `skills/houmao-agent-ag-ui` retired projection
- **AND THEN** it projects the current skill at `skills/houmao-interop-ag-ui`
