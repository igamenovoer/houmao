## ADDED Requirements

### Requirement: Project-local auth profiles use catalog-owned opaque storage identity
Project-local auth profiles SHALL be stored as catalog-owned semantic objects with distinct operator-facing display names and stable opaque storage identity.

At minimum, each persisted auth profile SHALL carry:

- the selected tool family,
- a mutable display name unique within that tool family,
- an immutable opaque bundle reference used for file-backed auth content storage and compatibility projection,
- a managed content reference for the auth payload.

Managed auth content SHALL be stored under bundle-reference-keyed managed content paths rather than display-name-keyed managed content paths.

Directory basenames under managed auth content or compatibility projection trees SHALL NOT be treated as the semantic identity of an auth profile.

#### Scenario: Newly created auth profile receives opaque storage identity
- **WHEN** an operator creates a new project-local Claude auth profile named `personal`
- **THEN** the catalog persists that auth profile with display name `personal`
- **AND THEN** the backing auth content is stored and later projected under an opaque bundle-reference path rather than a display-name-derived path

#### Scenario: Renaming auth profile does not change bundle-reference-backed content storage
- **WHEN** a project-local auth profile already exists with display name `work`
- **AND WHEN** that auth profile is renamed to `breakglass`
- **THEN** the catalog keeps the same opaque bundle reference and managed content reference for that auth profile
- **AND THEN** only the display-name metadata changes

### Requirement: Project-local auth relationships resolve through auth profile identity
Persisted project-local relationships that target auth profiles SHALL resolve through auth profile identity rather than storing auth display-name text as the relationship key.

At minimum, launch-profile auth overrides and specialist-owned auth selection SHALL resolve through the referenced auth profile instead of duplicating display-name identity as authoritative state.

User-facing inspection surfaces MAY render the current auth display name, but that rendered name SHALL be derived from the referenced auth profile rather than treated as the stored relationship key.

#### Scenario: Launch-profile auth relationship remains valid after auth rename
- **WHEN** an explicit launch profile references one existing Codex auth profile
- **AND WHEN** that auth profile is renamed from `work` to `breakglass`
- **THEN** the launch profile still resolves the same auth profile without requiring a launch-profile edit
- **AND THEN** later inspection renders the current display name `breakglass`

#### Scenario: Specialist inspection derives auth name from the referenced auth profile
- **WHEN** a persisted specialist references one existing auth profile
- **AND WHEN** that auth profile has display name `reviewer-creds`
- **THEN** specialist inspection renders `reviewer-creds` as the selected auth name
- **AND THEN** that rendered name comes from the referenced auth profile instead of a second authoritative stored name field
