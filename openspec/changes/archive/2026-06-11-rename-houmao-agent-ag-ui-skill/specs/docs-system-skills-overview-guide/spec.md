## ADDED Requirements

### Requirement: Overview guide lists the renamed AG-UI interop skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-interop-ag-ui` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-interop-ag-ui` as the AG-UI interop skill for Houmao typed component authoring, AG-UI event rendering, gateway publishing, GUI delivery interpretation, and UI payload safety.

The guide SHALL NOT list `houmao-agent-ag-ui` as a current packaged skill.

If the guide mentions retired names, it SHALL identify `houmao-agent-ag-ui` only as the retired previous name for `houmao-interop-ag-ui`.

#### Scenario: Reader sees the renamed AG-UI interop skill
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-interop-ag-ui` among the packaged Houmao-owned system skills
- **AND THEN** it describes the skill as interop guidance for Houmao component messages carried over AG-UI

#### Scenario: Guide does not present the old name as current
- **WHEN** a reader checks the current packaged skill list in the overview guide
- **THEN** the guide does not list `houmao-agent-ag-ui` as a current packaged skill
- **AND THEN** any mention of `houmao-agent-ag-ui` identifies it as the retired previous name
