## ADDED Requirements

### Requirement: CLI reference documents the graphing extension skill
The CLI reference page `docs/reference/cli/system-skills.md` SHALL describe `houmao-ext-graphing` as a packaged Houmao-owned system skill.

That page SHALL describe `houmao-ext-graphing` as the extension skill for built-in Plotly.js templated graphics and Vega-Lite freeform graphics authoring over Houmao AG-UI implementation schemas.

The page SHALL NOT describe `houmao-utils-graphing` as a current packaged skill, current set member, install example, status result, or uninstall target except as a retired skill projection that may be removed.

#### Scenario: Reader sees the graphing extension in the system-skills reference
- **WHEN** a reader opens `docs/reference/cli/system-skills.md`
- **THEN** the page lists `houmao-ext-graphing` as a current packaged skill
- **AND THEN** it describes the skill as extension graphing authoring guidance
- **AND THEN** it does not list `houmao-utils-graphing` as current

### Requirement: CLI reference documents extensions set behavior
The CLI reference page `docs/reference/cli/system-skills.md` SHALL document `core`, `extensions`, and `all` as the current installable named sets.

The page SHALL state that managed launch and managed join auto-install `core` plus `extensions`.

The page SHALL state that omitted-selection `houmao-mgr system-skills install` resolves `all`.

The page SHALL explain that `core` is the non-extension baseline, `extensions` contains default-installed extension skills, and `all` includes both core and extension skills.

#### Scenario: Reader sees current named sets and defaults
- **WHEN** a reader checks install-selection behavior in `docs/reference/cli/system-skills.md`
- **THEN** the page documents `core`, `extensions`, and `all`
- **AND THEN** it documents `managed_launch_sets = ["core", "extensions"]`, `managed_join_sets = ["core", "extensions"]`, and `cli_default_sets = ["all"]`

#### Scenario: Reader understands explicit core excludes extensions
- **WHEN** the CLI reference shows resolved set examples
- **THEN** the `core` example does not include `houmao-ext-graphing`
- **AND THEN** the `extensions` or `all` example includes `houmao-ext-graphing`

### Requirement: CLI reference explains retired graphing utility cleanup
The CLI reference page `docs/reference/cli/system-skills.md` SHALL explain that known retired Houmao skill projections, including `houmao-utils-graphing`, may be removed during current install or uninstall operations.

#### Scenario: Reader understands old graphing utility removal
- **WHEN** a reader checks install or uninstall cleanup semantics
- **THEN** the page explains that `houmao-utils-graphing` is a retired projection name
- **AND THEN** the page explains that current install or uninstall operations may remove that stale Houmao-owned projection
