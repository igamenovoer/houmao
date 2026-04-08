## ADDED Requirements

### Requirement: Managed force takeover supports explicit home reuse and clean rebuild policies

When brain construction is invoked for managed force takeover of an existing managed home, the system SHALL support home policies `keep-stale` and `clean`.

Fresh-by-default home creation SHALL remain the default when no explicit managed takeover home policy is requested.

For `keep-stale`, construction SHALL reuse the existing managed home path in place and SHALL overwrite only the setup, skill, auth, model, and helper outputs that the new build projects.

For `keep-stale`, untouched existing files in that managed home SHALL remain in place.

For `clean`, construction SHALL remove the existing managed home directory and recreate an empty managed home before projection begins.

For both policies, construction SHALL rewrite the managed build manifest for the reused managed home to reflect the replacement build outputs.

Managed-home cleanup SHALL apply only to the targeted Houmao-managed home and SHALL NOT delete arbitrary caller-owned directories.

#### Scenario: Ordinary construction remains fresh by default
- **WHEN** brain construction runs without an explicit managed takeover home policy
- **THEN** it creates a fresh managed home rather than reusing an existing one

#### Scenario: `keep-stale` preserves untouched files in the reused home
- **WHEN** an existing managed home contains a stale file that the new build will not project
- **AND WHEN** construction runs with home policy `keep-stale`
- **THEN** the builder leaves that stale file in place
- **AND THEN** it still overwrites the projection targets written by the new build

#### Scenario: `clean` recreates an empty managed home before projection
- **WHEN** an existing managed home already exists for the target managed identity
- **AND WHEN** construction runs with home policy `clean`
- **THEN** the builder removes that managed home
- **AND THEN** it recreates an empty managed home before projecting the replacement build outputs
