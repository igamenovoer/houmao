## ADDED Requirements

### Requirement: Houmao-owned system skills use a flat packaged asset layout
The system SHALL package each current Houmao-owned system skill as one top-level directory directly under the maintained system-skill asset root.

For each current packaged skill, the catalog `asset_subpath` SHALL equal that skill directory name and SHALL NOT include a family namespace segment such as `mailbox/` or `project/`.

The packaged asset tree SHALL NOT require family-specific subdirectories to distinguish mailbox-oriented skills from project-oriented skills.

#### Scenario: Maintainer inspects the packaged skill asset root
- **WHEN** a maintainer inspects the maintained Houmao-owned system-skill asset root
- **THEN** each current skill lives under `src/houmao/agents/assets/system_skills/<houmao-skill>/`
- **AND THEN** the packaged catalog uses `<houmao-skill>` as that skill's `asset_subpath`
- **AND THEN** the maintained asset root does not rely on `mailbox/` or `project/` subdirectories for current skills

### Requirement: Grouping is expressed through reserved names and named sets rather than filesystem families
The system SHALL use reserved `houmao-` skill names and named skill sets to distinguish and group Houmao-owned system skills.

Logical groupings such as mailbox workflows and project-easy authoring SHALL be represented through catalog sets, descriptions, or docs rather than through visible installed path segments or packaged family directory names.

#### Scenario: Operator inspects current Houmao-owned skill inventory
- **WHEN** an operator lists the packaged Houmao-owned system skills and named sets
- **THEN** the current skills remain distinguishable through their reserved `houmao-` names
- **AND THEN** mailbox-oriented and project-oriented groupings remain expressible through named sets such as `mailbox-full` and `project-easy`
- **AND THEN** those groupings do not require `mailbox/` or `project/` filesystem namespaces
