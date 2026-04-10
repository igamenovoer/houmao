## ADDED Requirements

### Requirement: Packaged system-skill catalog includes `houmao-touring` and a dedicated touring set
The packaged current-system-skill catalog SHALL include `houmao-touring` as a current installable Houmao-owned system skill.

That packaged skill SHALL use `houmao-touring` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define a dedicated named set `touring` whose only member is `houmao-touring`.

The packaged catalog's fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` SHALL include the dedicated `touring` named set.

The packaged catalog SHALL keep `houmao-touring` in the dedicated `touring` set rather than folding it into `user-control`, `advanced-usage`, `agent-instance`, `agent-messaging`, or `agent-gateway`.

#### Scenario: Maintainer inspects the packaged catalog and sees the touring skill
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-touring`
- **AND THEN** the packaged catalog defines a dedicated `touring` named set containing only that skill

#### Scenario: Fixed default selections include the touring set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets`
- **THEN** each fixed selection includes the dedicated `touring` named set
- **AND THEN** the touring skill becomes part of the resolved default packaged skill inventory without being folded into another named set
