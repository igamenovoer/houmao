## ADDED Requirements

### Requirement: CAO server launcher archived history is self-contained
Archived OpenSpec artifacts for `cao-server-launcher` SHALL keep required
historical references self-contained within `gig-agents`.

If an archived launcher artifact depends on a referenced document that did not
exist in `gig-agents`, that reference SHALL be localized by copying the required
artifact into `gig-agents` with preserved directory structure or by replacing
the reference with an equivalent local path.

#### Scenario: Launcher archived artifact uses localized references
- **WHEN** a `cao-server-launcher` archived artifact references supporting context
- **THEN** the referenced context exists under `gig-agents`
- **AND THEN** readers do not need access to files outside this repository

### Requirement: CAO launcher archived artifacts avoid stale active-change links
Archived `cao-server-launcher` artifacts SHALL not retain stale
`openspec/changes/<id>/...` links when the target change is archived.

#### Scenario: Launcher archived link is rewritten to archive path
- **WHEN** a `cao-server-launcher` archived artifact links to another archived OpenSpec artifact
- **THEN** the link uses `openspec/changes/archive/<date>-<id>/...`
- **AND THEN** the target path resolves in `gig-agents`
