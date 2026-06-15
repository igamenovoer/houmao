## MODIFIED Requirements

### Requirement: Overview guide lists the renamed AG-UI interop skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-interop-ag-ui` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-interop-ag-ui` as the AG-UI protocol and gateway interop skill for standard event validation, protocol event rendering, generic implementation rendering, gateway publishing, GUI delivery interpretation, endpoint boundaries, routing, and UI payload safety.

The guide SHALL state that built-in Plotly.js and Vega-Lite graphing authoring belongs to `houmao-utils-graphing`.

The guide SHALL NOT list `houmao-agent-ag-ui` as a current packaged skill.

If the guide mentions retired names, it SHALL identify `houmao-agent-ag-ui` only as the retired previous name for `houmao-interop-ag-ui`.

#### Scenario: Reader sees the renamed AG-UI interop skill
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-interop-ag-ui` among the packaged Houmao-owned system skills
- **AND THEN** it describes the skill as AG-UI protocol and gateway interop guidance
- **AND THEN** it points built-in graphing authoring to `houmao-utils-graphing`

#### Scenario: Guide does not present the old name as current
- **WHEN** a reader checks the current packaged skill list in the overview guide
- **THEN** the guide does not list `houmao-agent-ag-ui` as a current packaged skill
- **AND THEN** any mention of `houmao-agent-ag-ui` identifies it as the retired previous name

## ADDED Requirements

### Requirement: Overview guide lists the graphing utility skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-utils-graphing` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-utils-graphing` as the utility skill for built-in Plotly.js templated graphics and Vega-Lite freeform graphics authoring over Houmao AG-UI implementation schemas.

The guide SHALL identify the canonical routing for `houmao-utils-graphing` as `houmao-mgr ag-ui impl templated-graphics list`, `houmao-mgr ag-ui impl freeform-graphics list`, `houmao-mgr ag-ui impl schema ...`, `houmao-mgr ag-ui impl catalog houmao.graphic.template traces`, `houmao-mgr ag-ui impl validate ...`, and `houmao-mgr ag-ui impl render ...`.

The guide SHALL distinguish `houmao-utils-graphing` from `houmao-interop-ag-ui` by stating that graphing authors payloads while interop publishes and interprets AG-UI delivery.

#### Scenario: Reader sees the graphing utility in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-utils-graphing` among the packaged Houmao-owned system skills
- **AND THEN** it describes Plotly.js and Vega-Lite graphing authoring as that skill's responsibility

#### Scenario: Reader can distinguish graphing from interop
- **WHEN** a reader compares the `houmao-utils-graphing` and `houmao-interop-ag-ui` rows
- **THEN** the graphing row covers built-in graphing payload authoring
- **AND THEN** the interop row covers protocol validation, event rendering mechanics, gateway publishing, and delivery interpretation
