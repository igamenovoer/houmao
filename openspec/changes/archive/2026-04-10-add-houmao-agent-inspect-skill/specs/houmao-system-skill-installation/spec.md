## ADDED Requirements

### Requirement: Packaged system-skill catalog includes `houmao-agent-inspect` and a dedicated inspect set
The packaged current-system-skill catalog SHALL include `houmao-agent-inspect` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-agent-inspect` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog SHALL define a dedicated named set `agent-inspect` whose only member is `houmao-agent-inspect`.

The packaged catalog's fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` SHALL include the dedicated `agent-inspect` named set.

The packaged catalog SHALL keep `houmao-agent-inspect` in the dedicated `agent-inspect` set rather than folding it into `user-control`, `agent-instance`, `agent-messaging`, or `agent-gateway`.

#### Scenario: Maintainer inspects the packaged catalog and sees the inspect skill
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-agent-inspect`
- **AND THEN** the packaged catalog defines a dedicated `agent-inspect` named set containing only that skill

#### Scenario: Fixed default selections include the inspect set
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets`
- **THEN** each fixed selection includes the dedicated `agent-inspect` named set
- **AND THEN** the inspect skill becomes part of the resolved default packaged skill inventory without being folded into another named set
