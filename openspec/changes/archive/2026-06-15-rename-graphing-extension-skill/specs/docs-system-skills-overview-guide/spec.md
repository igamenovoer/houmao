## MODIFIED Requirements

### Requirement: System-skills overview guide avoids stale counts
The overview guide narrative SHALL NOT state a frozen skill count that does not match the current `catalog.toml` entry count and the resolved `[auto_install]` set contents.

Where the guide references how many skills exist, how many are auto-installed by `agents launch` or `agents join`, or how many are installed by `system-skills install` when no `--skill-set` or `--skill` is supplied, those numbers SHALL be computed from the current catalog rather than copied as literal text.

The guide SHALL describe managed launch and join as resolving `core` plus `extensions`, and omitted-selection CLI installs as resolving `all`.

#### Scenario: Overview avoids stale skill counts
- **WHEN** a reader reads the overview guide paragraphs that introduce the packaged system skills
- **THEN** those paragraphs do not assert a total skill count that contradicts `catalog.toml`
- **AND THEN** they do not assert an auto-install skill count that contradicts the resolved `managed_launch_sets`, `managed_join_sets`, or `cli_default_sets` expansions

#### Scenario: Overview auto-install wording tracks core, extensions, and all
- **WHEN** a reader inspects the auto-install guidance in the overview guide
- **THEN** the guide states that managed launch and join use `core` plus `extensions`
- **AND THEN** it states that omitted-selection `houmao-mgr system-skills install` uses `all`
- **AND THEN** it does not describe removed granular set names as current installable sets

### Requirement: System-skills overview guide explains organization groups and installable sets
The system-skills overview guide SHALL explain that automation, control, utils, and extensions are organization groups used for documentation readability.

The guide SHALL explain that the current installable named sets are `core`, `extensions`, and `all`.

The guide SHALL state that `core` is the non-extension baseline, `extensions` contains default-installed extension skills, managed launch and managed join install `core` plus `extensions`, and `all` is the omitted-selection CLI install default.

#### Scenario: Reader distinguishes organization groups from installable sets
- **WHEN** a reader opens the system-skills overview guide
- **THEN** they can distinguish automation/control/utils/extensions organization groups from the installable `core`, `extensions`, and `all` set names
- **AND THEN** install examples use `core`, `extensions`, `all`, or explicit skill names

## ADDED Requirements

### Requirement: System-skills overview guide lists the graphing extension skill
The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL list `houmao-ext-graphing` as one of the currently shipped packaged Houmao-owned system skills.

The guide SHALL describe `houmao-ext-graphing` as the extension skill for built-in Plotly.js templated graphics and Vega-Lite freeform graphics authoring over Houmao AG-UI implementation schemas.

The guide SHALL NOT list `houmao-utils-graphing` as a current packaged skill.

The guide SHALL describe `houmao-ext-graphing` as part of the `extensions` group and current `extensions` named set.

#### Scenario: Reader sees the graphing extension in the narrative guide
- **WHEN** a reader opens `docs/getting-started/system-skills-overview.md`
- **THEN** the guide lists `houmao-ext-graphing` among the packaged Houmao-owned system skills
- **AND THEN** it describes Plotly.js and Vega-Lite graphing authoring as that extension skill's responsibility
- **AND THEN** it does not list `houmao-utils-graphing` as current

### Requirement: System-skills overview guide explains extension routing boundary
The getting-started guide SHALL explain that extension skills may be installed by default but remain ignorable by users who do not want that guidance.

The guide SHALL state that non-extension skills do not depend on or route to extension skills.

The guide SHALL distinguish `houmao-ext-graphing` from `houmao-interop-ag-ui` by stating that graphing authors payloads while interop validates, renders, publishes, and interprets AG-UI delivery for already-chosen payloads and rendered events.

#### Scenario: Reader understands default-installed extensions are optional guidance
- **WHEN** a reader compares `core` and `extensions` in the overview guide
- **THEN** the guide explains that extensions are default-installed through the default set selection
- **AND THEN** it explains that core and other non-extension skills remain usable when extension guidance is ignored

#### Scenario: Reader can distinguish graphing from interop
- **WHEN** a reader compares the `houmao-ext-graphing` and `houmao-interop-ag-ui` rows
- **THEN** the graphing row covers built-in graphing payload authoring
- **AND THEN** the interop row covers AG-UI protocol, implementation rendering for already-chosen payloads, gateway publishing, and delivery-result interpretation
