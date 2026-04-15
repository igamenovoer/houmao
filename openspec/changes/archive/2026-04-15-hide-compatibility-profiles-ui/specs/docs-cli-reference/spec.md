## ADDED Requirements

### Requirement: CLI reference hides compatibility-profile bootstrap
The CLI reference SHALL NOT document `--with-compatibility-profiles` as an option for `houmao-mgr project init`.

The CLI reference SHALL NOT present `.houmao/agents/compatibility-profiles/` as a supported project-layout directory, bootstrap result, optional project-init workflow, or operator-authored compatibility metadata root.

If CLI reference content mentions internal CAO compatibility elsewhere, that content SHALL remain scoped to the relevant legacy or compatibility runtime surface and SHALL NOT direct operators to author or pre-create compatibility profile files.

#### Scenario: Reader sees no compatibility-profile project-init option
- **WHEN** a reader opens CLI reference coverage for `houmao-mgr project init`
- **THEN** the reference does not list `--with-compatibility-profiles`
- **AND THEN** the reference does not include an example that creates `.houmao/agents/compatibility-profiles/`

#### Scenario: Reader sees no compatibility-profile project layout guidance
- **WHEN** a reader scans CLI reference project-layout notes
- **THEN** the reference does not present `.houmao/agents/compatibility-profiles/` as a maintained local project directory
