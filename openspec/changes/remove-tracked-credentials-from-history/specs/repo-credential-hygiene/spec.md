## ADDED Requirements

### Requirement: Reachable repository history excludes tracked credential payloads

The repository SHALL ensure that credential-bearing fixture payloads such as live `auth.json`, OAuth token dumps, or similar auth artifacts are absent from reachable branch or tag history intended for normal new clones.

Refs kept for normal fetches SHALL be rewritten or force-updated as needed so a fresh clone of supported public branches does not materialize the removed credential payloads from reachable history.

#### Scenario: Fresh clone of the cleaned default branch does not contain removed auth payload

- **WHEN** an operator clones the repository after the cleanup and checks out a supported public branch
- **THEN** the clone SHALL NOT contain the removed tracked `tests/fixtures/agents/tools/codex/auth/personal-a-default/files/auth.json` payload from reachable branch history

#### Scenario: Remaining remote refs are checked for leaked commit reachability

- **WHEN** the cleanup force-updates the rewritten history
- **THEN** repo-owned branches and tags that remain available for normal fetches SHALL be checked so they do not still reference the removed credential-bearing commit

### Requirement: Credential-bearing repo files are ignored by default

The repository SHALL ignore credential-bearing auth files by default, including auth env files, `auth.json`, OAuth token payloads, and similar secret-bearing artifacts under fixture or demo auth directories, unless a file is explicitly tracked as a documented secret-free placeholder or template.

Ignore rules SHALL be specific enough that new real credentials created under repo auth trees remain untracked without relying on operator memory.

#### Scenario: Local auth env file remains untracked

- **WHEN** a developer creates or updates a credential env file under a repo auth directory
- **THEN** git SHALL treat that file as ignored by default

#### Scenario: New auth payload dump remains untracked

- **WHEN** a developer creates a local `auth.json` or OAuth token payload under a repo auth directory
- **THEN** git SHALL treat that file as ignored by default unless the path is explicitly allowlisted for a secret-free placeholder or template

### Requirement: Tracked auth fixtures are secret-free

Tracked auth fixture files kept in the repository SHALL contain only empty objects, inert placeholders, or documented bootstrap templates with no live secrets.

The repository SHALL NOT track live access tokens, refresh tokens, API keys, session exports, or equivalent credential material in fixture auth files.

#### Scenario: Placeholder OAuth fixture remains trackable

- **WHEN** the repository needs to keep an OAuth-shaped fixture file for test structure
- **THEN** that file SHALL use inert placeholder values rather than live tokens

#### Scenario: Empty credential file remains trackable

- **WHEN** the repository needs to keep a credential file path for fixture structure
- **THEN** the tracked file SHALL use an empty object or other secret-free stub content
