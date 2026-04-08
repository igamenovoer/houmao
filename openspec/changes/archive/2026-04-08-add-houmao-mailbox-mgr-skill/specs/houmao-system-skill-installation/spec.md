## ADDED Requirements

### Requirement: Packaged system-skill catalog includes mailbox-administration guidance and expands `mailbox-full`
The packaged current-system-skill catalog SHALL include `houmao-mailbox-mgr` as a current installable Houmao-owned skill.

That packaged skill SHALL use `houmao-mailbox-mgr` as both its catalog key and its packaged `asset_subpath`.

The packaged catalog's `mailbox-core` named set SHALL continue to include only:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The packaged catalog's `mailbox-full` named set SHALL include:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`
- `houmao-mailbox-mgr`

The packaged catalog's fixed `managed_launch_sets`, `managed_join_sets`, and `cli_default_sets` selections MAY remain unchanged as named-set lists when those selections already include `mailbox-full`.

When those fixed selections resolve `mailbox-full`, the resolved installed skill list SHALL include `houmao-mailbox-mgr` together with the existing mailbox worker pair.

#### Scenario: Maintainer sees the packaged mailbox-admin skill and expanded full mailbox set
- **WHEN** a maintainer inspects the packaged current-system-skill catalog
- **THEN** the current installable skill inventory includes `houmao-mailbox-mgr`
- **AND THEN** `mailbox-core` remains the two-skill mailbox worker pair
- **AND THEN** `mailbox-full` resolves the worker pair plus `houmao-mailbox-mgr`

#### Scenario: Existing fixed auto-install selections pick up the mailbox-admin skill through `mailbox-full`
- **WHEN** a maintainer inspects the packaged `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets`
- **AND WHEN** those fixed set lists still include `mailbox-full`
- **THEN** the resolved install selection includes `houmao-mailbox-mgr`
- **AND THEN** the change does not require a separate fixed auto-install set just to surface mailbox-administration guidance
