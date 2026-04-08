## ADDED Requirements

### Requirement: Packaged system-skill catalog includes the advanced-usage skill and default set selection
The packaged current-system-skill catalog SHALL include `houmao-adv-usage-pattern` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-adv-usage-pattern` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define a dedicated named set for that skill rather than folding it silently into an unrelated existing set.

The packaged catalog's fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` selections SHALL include that dedicated advanced-usage set so the packaged advanced skill is installed by default in managed homes and default external-home installs.

#### Scenario: Maintainer sees the advanced-usage skill in the packaged catalog
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-adv-usage-pattern`
- **AND THEN** the catalog defines a dedicated named set for that skill using the same flat packaged asset-path model as the other current skills

#### Scenario: Default install selections include the advanced-usage set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets`
- **THEN** each fixed selection includes the dedicated advanced-usage set
- **AND THEN** the default resolved install list for managed homes and CLI-default installs includes `houmao-adv-usage-pattern`

