# houmao-system-skill-version-metadata Specification

## Purpose
Tie the six released system-skill trees to the Houmao release through root frontmatter and matching Git tags. Validate the versions in source and distributions, and read installed metadata for diagnostics.
## Requirements

### Requirement: Standalone system skills declare their Houmao release
Each of the six standalone `SKILL.md` files SHALL declare exactly one quoted, nonempty `metadata.houmao_version` YAML value equal to the project release. That value SHALL apply to its complete owned tree. Parent-scoped `SKILL-MAIN.md` children SHALL inherit the containing release and SHALL NOT declare independent `houmao_version` values.

#### Scenario: Release source contains the six static roots
- **WHEN** source validation inspects the public system-skill collection
- **THEN** every standalone `SKILL.md` reports the project release version from `metadata.houmao_version`
- **AND THEN** no shared child `SKILL-MAIN.md` reports an independent Houmao version

#### Scenario: Shared routines owns versioned children
- **WHEN** an operator inspects the installed `houmao-shared-routines` root
- **THEN** its `SKILL.md` declares `metadata.houmao_version`
- **AND THEN** that version covers all child trees declared for the shared root

### Requirement: Release validation keeps static assets synchronized
Source and distribution validation SHALL compare `metadata.houmao_version` in all six standalone roots with `[project].version` from `pyproject.toml`. The tagged release build SHALL fail before distribution publication if a root has missing, duplicate, unquoted, non-string, malformed, or mismatching release metadata. Wheel and sdist validation SHALL confirm those values in packaged assets.

#### Scenario: Project version is bumped without skill metadata
- **WHEN** a release build sees a standalone root whose `metadata.houmao_version` differs from the project version
- **THEN** release validation fails before building or publishing distributions
- **AND THEN** it identifies the mismatched skill and both version strings

#### Scenario: Distribution contains current metadata
- **WHEN** wheel and sdist contents are inspected
- **THEN** both artifacts contain all six standalone roots with the project release version under `metadata.houmao_version`
- **AND THEN** neither artifact adds version fields to shared child entrypoints

### Requirement: Released system skills publish under matching Git tags
Publishing a Houmao GitHub release SHALL copy the complete public system-skill directories to the repository root of `igamenovoer/houmao-skills` and SHALL create an immutable tag whose name matches the Houmao release tag.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The mirror's `main` branch SHALL track the latest stable Houmao release. Publishing a prerelease SHALL create its matching tag without advancing `main`. The release workflow SHALL validate the release tag against `[project].version`, validate standalone `metadata.houmao_version`, and validate Skills CLI discovery before publishing.

#### Scenario: Stable release publishes the default collection
- **WHEN** a stable Houmao release named `vX.Y.Z` is published
- **THEN** `houmao-skills` receives an immutable `vX.Y.Z` tag containing the released public skills at repository root
- **AND THEN** `houmao-skills/main` advances to the same released skill tree

#### Scenario: Prerelease preserves the stable default
- **WHEN** a Houmao prerelease named `vX.Y.ZrcN` is published
- **THEN** `houmao-skills` receives an immutable matching prerelease tag
- **AND THEN** `houmao-skills/main` remains on the latest stable release

#### Scenario: Existing tag differs from release content
- **WHEN** publication finds that the matching `houmao-skills` tag already exists with different content
- **THEN** publication fails instead of moving or replacing the existing tag

### Requirement: Installed version parsing is portable and read only
Doctor SHALL read `metadata.houmao_version` directly from each installed root's `SKILL.md` and report the observed version string. It SHALL report missing files, malformed frontmatter, duplicate keys, missing fields, non-string values, and malformed release values as diagnostic evidence. Parsing SHALL require no lifecycle config and SHALL leave installed files untouched.

#### Scenario: Skills CLI installation has no receipt
- **WHEN** doctor inspects a complete externally copied agent pack without Houmao ownership configuration
- **THEN** it reads each installed root's frontmatter directly
- **AND THEN** it can report version matches without creating lifecycle state

#### Scenario: Version field is malformed
- **WHEN** an installed root contains a non-string or invalid `metadata.houmao_version`
- **THEN** parsing reports the field as invalid for that root
- **AND THEN** the installed tree remains untouched

#### Scenario: Older skill declares version only at the top level
- **WHEN** doctor inspects a root with a top-level `houmao_version` and no `metadata.houmao_version`
- **THEN** doctor reports the canonical release field as missing
- **AND THEN** refreshing the tree through its supported installation or upgrade path installs current metadata

#### Scenario: Doctor reports observed release and configuration separately
- **WHEN** ownership configuration and installed frontmatter both declare versions
- **THEN** doctor reports those values separately using the existing machine-readable version fields
- **AND THEN** it compares the running release with the installed frontmatter value

### Requirement: Non-collection assets remain outside the system-skill version contract
The top-level version contract SHALL exclude legacy system skills, generated execplan skills, and project-authored skills.

The presence or absence of `houmao_version` in those excluded assets SHALL NOT affect system-skill doctor results for the static public collection. Provider-native system-prompt files SHALL be inspected through brain provenance rather than parsed as skills.

#### Scenario: Project-authored skill is installed
- **WHEN** doctor inspects a managed agent home containing a project-authored skill outside the static public collection
- **THEN** it does not require or compare `houmao_version` on that project-authored skill
- **AND THEN** it evaluates only the expected standalone static pack roots

#### Scenario: Managed Kimi native prompt is present
- **WHEN** doctor inspects a managed Kimi home containing `SYSTEM.md`
- **THEN** it does not treat the file as a system skill or require skill release metadata on it
- **AND THEN** system-prompt integrity remains the responsibility of brain provenance inspection
