## ADDED Requirements

### Requirement: Shared installer supports Copilot system-skill projection
The shared Houmao system-skill installer SHALL support Copilot as a current explicit installation target without adding Copilot-specific catalog entries.

For Copilot, the visible projected path relative to the resolved target home SHALL be `skills/<houmao-skill>/`.

The shared installer SHALL preserve the same selection, projection-mode, status-discovery, and owned-path replacement semantics for Copilot that it uses for other supported explicit tool homes.

#### Scenario: Explicit copy installation projects one selected current skill into a Copilot home
- **WHEN** an operator installs one selected current Houmao-owned skill into a Copilot home without requesting symlink mode
- **THEN** the installer projects that skill under `skills/<houmao-skill>/` as copied content
- **AND THEN** it does not require a copied project-local skill mirror outside the resolved Copilot home

#### Scenario: Explicit symlink installation projects one selected current skill into a Copilot home
- **WHEN** an operator installs one selected current Houmao-owned skill into a Copilot home and explicitly requests symlink mode
- **THEN** the installer projects that skill under `skills/<houmao-skill>/` as a directory symlink
- **AND THEN** the symlink target is the absolute filesystem path of the packaged skill asset directory

#### Scenario: Copilot status discovers installed current skills
- **WHEN** a resolved Copilot home contains current Houmao-owned system skills under `skills/<houmao-skill>/`
- **THEN** shared status discovery reports those current skill names
- **AND THEN** it reports whether each discovered current skill is projected as `copy` or `symlink`
