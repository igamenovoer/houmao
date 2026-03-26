## ADDED Requirements

### Requirement: Retired CAO reference docs deleted

The following files SHALL be deleted from `docs/reference/`: `cao_interactive_demo.md`, `cao_server_launcher.md`, `cao_shadow_parser_troubleshooting.md`, `cao_claude_shadow_parsing.md`. These are already marked as RETIRED and describe removed workflows.

#### Scenario: No CAO-prefixed reference files remain

- **WHEN** listing files in `docs/reference/`
- **THEN** no files with `cao_` prefix exist

### Requirement: Migration section deleted

The entire `docs/migration/` directory SHALL be deleted, including all 6 files (`migration-guide.md`, `runtime_migration_report.md`, `runtime_migration_parity_checklist.md`, `houmao/server-pair/README.md`, `tested.md`, and any subdirectories). These describe a completed CAO→Houmao transition.

#### Scenario: No migration directory exists

- **WHEN** listing directories under `docs/`
- **THEN** no `migration/` directory exists

### Requirement: Demo pack references removed from all docs

All references to `scripts/demo/` paths, demo pack names (e.g., `*-demo-pack`), and demo walkthrough instructions SHALL be removed from all files under `docs/`. Documentation SHALL reference source modules and CLI commands instead.

#### Scenario: No demo pack references in docs

- **WHEN** searching all `.md` files under `docs/` for `scripts/demo/` or `-demo-pack`
- **THEN** zero matches are found

### Requirement: Internal cross-references updated after deletions

After deleting retired files and the migration section, all remaining docs SHALL be checked for broken internal links pointing to deleted files. Broken links SHALL be removed or redirected to the relevant replacement page.

#### Scenario: No broken internal links to deleted files

- **WHEN** searching remaining docs for links to deleted filenames (e.g., `cao_interactive_demo.md`, `migration-guide.md`)
- **THEN** zero matches are found

### Requirement: Remaining files cleaned of CAO-primary framing

Files that are retained (not deleted or fully rewritten) SHALL have CAO references reduced to factual mentions where technically necessary (e.g., "the `cao_rest` backend exists as a legacy path"). CAO SHALL NOT appear as a primary workflow, architecture pillar, or recommended path in any retained file.

#### Scenario: CAO appears only as legacy reference in retained files

- **WHEN** searching retained docs for "CAO"
- **THEN** each occurrence is in context of legacy/compatibility description, not as a primary workflow recommendation
