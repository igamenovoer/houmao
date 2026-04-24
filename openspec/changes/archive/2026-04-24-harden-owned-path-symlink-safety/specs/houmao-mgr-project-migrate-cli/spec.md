## ADDED Requirements

### Requirement: `project migrate` preserves external source trees during canonicalization
When `houmao-mgr project migrate --apply` imports legacy project skill or related content into the current overlay model, the command SHALL treat repo-owned or otherwise external source paths as read-only inputs.

`project migrate` SHALL mutate only Houmao-managed overlay artifact paths while canonicalizing content under `.houmao/`.

#### Scenario: Canonicalizing a legacy symlink-backed skill preserves the repo source directory
- **WHEN** the selected project overlay still exposes one legacy compatibility-tree skill entry that resolves to one repo-owned source directory
- **AND WHEN** an operator runs `houmao-mgr project migrate --apply`
- **THEN** the command creates or refreshes canonical managed skill content under `.houmao/content/skills/`
- **AND THEN** the repo-owned source directory remains intact

#### Scenario: Failed migration does not consume source content
- **WHEN** one supported migration step reads legacy compatibility-tree content from one external or repo-owned source path
- **AND WHEN** `houmao-mgr project migrate --apply` fails after mutating only Houmao-managed overlay artifacts
- **THEN** the source path remains intact
