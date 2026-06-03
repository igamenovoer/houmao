## MODIFIED Requirements

### Requirement: Utility logical group is included through all
The packaged current system-skill catalog SHALL include general utility skills in the `all` named set.

The utility logical group SHALL include `houmao-utils-workspace-mgr`.

The utility logical group SHALL NOT include `houmao-utils-llm-wiki`.

The utility logical group SHALL NOT be installed by managed launch or managed join defaults unless a future change adds utility skills to `core`.

#### Scenario: CLI default installation includes utility group
- **WHEN** an operator installs system skills without `--skill-set` or `--skill`
- **THEN** the resolved CLI-default selection expands `all`
- **AND THEN** the resolved selection includes `houmao-utils-workspace-mgr`
- **AND THEN** the resolved selection does not include `houmao-utils-llm-wiki`

#### Scenario: Managed default installation omits utility group
- **WHEN** Houmao installs system skills for managed launch or join
- **THEN** the resolved selection expands `core`
- **AND THEN** the resolved selection omits the utility logical group
