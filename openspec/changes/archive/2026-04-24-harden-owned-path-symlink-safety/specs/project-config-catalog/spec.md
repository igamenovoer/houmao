## ADDED Requirements

### Requirement: Project catalog mutations stay within overlay-owned lexical artifact paths
Project catalog writes, replacements, and removals SHALL mutate only lexical artifact paths under the active overlay's managed content and projection roots.

This safety rule SHALL apply to managed content and projection flows for at least:
- project skills,
- auth profiles,
- setup snapshots,
- prompt-overlay payloads,
- memo-seed payloads,
- derived compatibility projections.

Catalog code MAY resolve managed content references for read-only validation, rendering, or digesting, but it SHALL NOT use those resolved paths as destructive mutation targets.

#### Scenario: Removing symlink-backed managed auth content preserves the target
- **WHEN** one project-local auth profile points at managed content whose artifact path under `.houmao/content/` is currently a symlink
- **AND WHEN** the operator removes that auth profile
- **THEN** the catalog removes only the lexical artifact path under `.houmao/content/`
- **AND THEN** it does not delete or rewrite the symlink target

#### Scenario: Replacing managed memo-seed content does not follow a pre-existing artifact symlink
- **WHEN** one launch-profile memo-seed artifact path under `.houmao/content/` currently exists as a symlink
- **AND WHEN** Houmao replaces that memo-seed content with new managed content
- **THEN** Houmao replaces only the managed artifact path inside `.houmao/content/`
- **AND THEN** it does not rewrite the symlink target
