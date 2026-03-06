## ADDED Requirements

### Requirement: Brain-launch-runtime archived history is gig-agents-native
Archived OpenSpec artifacts for `brain-launch-runtime` SHALL use
`gig-agents`-native references for runtime paths, design links, and supporting
context links.

Archived artifacts for this capability SHALL NOT require readers to access main
workspace files.

#### Scenario: Runtime archive artifact references local gig-agents paths
- **WHEN** a developer reads an archived `brain-launch-runtime` artifact
- **THEN** runtime code/document references resolve under `gig-agents`
- **AND THEN** legacy `agent_system_dissect` path references are not required for understanding the artifact

### Requirement: Brain-launch-runtime archive links are archive-stable
Archived `brain-launch-runtime` artifacts SHALL reference other OpenSpec
artifacts using archive-stable paths when those artifacts are archived.

#### Scenario: Runtime archived document points to archived peer change
- **WHEN** a `brain-launch-runtime` archived document links to another archived OpenSpec change artifact
- **THEN** the link target uses `openspec/changes/archive/<date>-<id>/...`
- **AND THEN** the link resolves within the `gig-agents` repository tree
