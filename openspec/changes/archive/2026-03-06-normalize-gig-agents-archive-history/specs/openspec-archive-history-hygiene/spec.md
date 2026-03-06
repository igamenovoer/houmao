## ADDED Requirements

### Requirement: Archived OpenSpec artifacts are repository-local and self-contained
Archived OpenSpec artifacts in `openspec/changes/archive/**` SHALL resolve all
required references from within the `gig-agents` repository.

Archived artifacts SHALL NOT depend on files that exist only in the main
workspace.

#### Scenario: Archived artifact contains only local-resolvable references
- **WHEN** a developer inspects an archived OpenSpec artifact in `openspec/changes/archive/**`
- **THEN** every required referenced file path resolves inside `gig-agents`
- **AND THEN** no required reference points to a main-workspace-only location

### Requirement: Legacy workspace path tokens are normalized in archived artifacts
Archived OpenSpec artifacts SHALL NOT contain legacy `agent_system_dissect`
module/path tokens where a `gig_agents`-native equivalent exists.

#### Scenario: Legacy module/path token is rewritten
- **WHEN** an archived artifact contains a legacy `agent_system_dissect` reference
- **THEN** the normalized artifact uses the corresponding `gig_agents` path/module form

### Requirement: Archived OpenSpec cross-links use archive-resolved paths
Archived markdown links that point to OpenSpec change artifacts SHALL use
archive-resolved locations when the target change is archived.

#### Scenario: Active-change path is normalized to archive path
- **WHEN** an archived artifact references `openspec/changes/<id>/...`
- **AND WHEN** `<id>` is represented under `openspec/changes/archive/<date>-<id>/...`
- **THEN** the link target is rewritten to the archive path

### Requirement: Archive-hygiene audit detects forbidden references
The repository SHALL provide an archive-reference audit check for migrated
OpenSpec history.

The audit SHALL fail when archived artifacts contain forbidden legacy references
or unresolved normalized targets.

#### Scenario: Audit fails on forbidden legacy reference
- **WHEN** an archived artifact includes a forbidden legacy pattern (for example `agent_system_dissect` or a main-workspace absolute path)
- **THEN** the archive-hygiene audit reports a failure identifying the violating artifact
