## ADDED Requirements

### Requirement: Gateway memory API preserves free-form memo ownership
The live gateway memory API SHALL treat `houmao-memo.md` as caller-owned free-form Markdown.

Gateway page operations SHALL NOT mutate `houmao-memo.md`.

The gateway SHALL NOT expose a memory reindex route or action.

#### Scenario: Gateway page write leaves memo unchanged
- **WHEN** a live gateway receives a request to write memory page `notes/run.md`
- **THEN** the gateway writes the contained page under `pages/notes/run.md`
- **AND THEN** the gateway does not update `houmao-memo.md`

#### Scenario: Gateway does not expose reindex
- **WHEN** a caller uses the supported gateway memory API
- **THEN** there is no supported route for rebuilding a memo page index

### Requirement: Gateway resolves memory page paths
The live gateway memory API SHALL expose a contained page path-resolution operation.

The response SHALL include the page-relative path, the memo-relative link string, the absolute filesystem path, existence state, and existing path kind when available.

The gateway SHALL reject path-resolution inputs that fail the managed page containment rules.

#### Scenario: Gateway resolves a contained future page
- **WHEN** a live gateway receives a path-resolution request for `notes/run.md`
- **AND WHEN** the path is contained under `pages/`
- **THEN** the gateway returns the absolute path for that page under the managed pages directory
- **AND THEN** the gateway returns `relative_link: pages/notes/run.md`

#### Scenario: Gateway rejects path escape resolution
- **WHEN** a live gateway receives a path-resolution request for `../secrets.md`
- **THEN** the gateway rejects the request
- **AND THEN** the gateway does not return an absolute escaped path
