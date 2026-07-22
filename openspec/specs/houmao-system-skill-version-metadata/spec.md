# houmao-system-skill-version-metadata Specification

## Purpose
TBD - created by archiving change add-system-skill-version-doctor. Update Purpose after archive.
## Requirements
### Requirement: Standalone system skills declare their Houmao release
Each of the six standalone public system-skill `SKILL.md` files SHALL declare exactly one quoted, non-empty `houmao_version` YAML frontmatter value equal to the Houmao project release version.

The version SHALL apply to the complete owned standalone tree. The sixteen parent-scoped `SKILL-MAIN.md` children SHALL NOT declare independent `houmao_version` values.

#### Scenario: Release source contains the six static roots
- **WHEN** source validation inspects the public system-skill collection
- **THEN** every standalone `SKILL.md` reports the project release version
- **AND THEN** no shared child `SKILL-MAIN.md` reports an independent Houmao version

#### Scenario: Shared routines owns versioned children
- **WHEN** an operator inspects the installed `houmao-shared-routines` root
- **THEN** its top-level `SKILL.md` declares the release version
- **AND THEN** that version covers all sixteen owned child trees

### Requirement: Non-collection skills remain outside the version contract
The top-level version contract SHALL exclude legacy system skills, generated execplan skills, project-authored skills, and the separately managed `houmao-auto-system-prompt` asset.

The presence or absence of `houmao_version` in those excluded assets SHALL NOT affect system-skill doctor results for the static public collection.

#### Scenario: Managed auto prompt is installed
- **WHEN** doctor inspects a managed agent home containing `houmao-auto-system-prompt`
- **THEN** it does not require or compare `houmao_version` on that auto skill
- **AND THEN** it evaluates only the expected standalone static pack roots

### Requirement: Release validation keeps static assets synchronized
Source and distribution validation SHALL compare each of the exact six standalone `houmao_version` strings with `[project].version` from `pyproject.toml`.

The tagged release build SHALL fail before distribution publication when a root is missing the field, declares a non-string or malformed value, contains duplicate version keys, or differs from the project version. Wheel and sdist validation SHALL confirm the same values in packaged assets.

#### Scenario: Project version is bumped without skill metadata
- **WHEN** a release build sees a standalone root whose `houmao_version` differs from the project version
- **THEN** the release validation fails before building or publishing distributions
- **AND THEN** it identifies the mismatched skill and both version strings

#### Scenario: Distribution contains current metadata
- **WHEN** wheel and sdist contents are inspected
- **THEN** both artifacts contain all six standalone roots with the project release version
- **AND THEN** neither artifact adds version fields to shared child entrypoints

### Requirement: Installed version parsing is portable and read only
The diagnostic parser SHALL read the installed top-level `SKILL.md` YAML frontmatter directly and SHALL preserve the observed `houmao_version` string for reporting.

Parsing SHALL NOT require a Houmao lifecycle receipt and SHALL NOT rewrite the skill. A missing file, malformed frontmatter, duplicate key, missing field, non-string field, or malformed release value SHALL produce explicit diagnostic evidence.

#### Scenario: Skills CLI installation has no receipt
- **WHEN** doctor inspects a complete externally copied agent pack without a Houmao receipt
- **THEN** it reads each installed root's frontmatter directly
- **AND THEN** it can report version matches without creating lifecycle state

#### Scenario: Version field is malformed
- **WHEN** an installed root contains a non-string or invalid `houmao_version`
- **THEN** parsing reports the field as invalid for that root
- **AND THEN** no install, upgrade, or repair action is attempted

