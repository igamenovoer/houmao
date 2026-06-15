## MODIFIED Requirements

### Requirement: Utility logical group is included through all
The packaged current system-skill catalog SHALL include general utility skills in the `all` named set.

The utility logical group SHALL include `houmao-utils-workspace-mgr`.

The utility logical group SHALL include `houmao-utils-graphing`.

The utility logical group SHALL NOT include `houmao-utils-llm-wiki`.

Utility skills that maintained core skills directly delegate to SHALL be included in the `core` named set.

The `core` and `all` named sets SHALL include `houmao-utils-graphing` when `houmao-interop-ag-ui` delegates built-in graphing authoring to it.

#### Scenario: CLI default installation includes utility group
- **WHEN** an operator installs system skills without `--skill-set` or `--skill`
- **THEN** the resolved CLI-default selection expands `all`
- **AND THEN** the resolved selection includes `houmao-utils-workspace-mgr`
- **AND THEN** the resolved selection includes `houmao-utils-graphing`
- **AND THEN** the resolved selection does not include `houmao-utils-llm-wiki`

#### Scenario: Managed default installation includes delegated graphing utility
- **WHEN** Houmao installs system skills for managed launch or join
- **THEN** the resolved selection expands `core`
- **AND THEN** the resolved selection includes `houmao-interop-ag-ui`
- **AND THEN** the resolved selection includes `houmao-utils-graphing`

#### Scenario: Utility skills keep flat projection
- **WHEN** Houmao installs `houmao-utils-graphing` into a supported tool home
- **THEN** the skill projects into the flat tool-native Houmao-owned skill root
- **AND THEN** the visible path does not include a family-specific utility subdirectory
