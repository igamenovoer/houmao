# agent-memory-freeform-memo Specification

## Purpose
Define the free-form ownership contract for managed-agent memo files and the page path-discovery metadata that lets callers author memo links explicitly.
## Requirements
### Requirement: Managed memory memo is free-form caller-owned Markdown
For each managed-agent memory root, Houmao SHALL treat `houmao-memo.md` as free-form Markdown owned by users and LLMs.

Houmao SHALL create `houmao-memo.md` when missing.

Houmao SHALL read, replace, or append `houmao-memo.md` only when the caller explicitly invokes a memo read, replace, or append operation, or when the caller explicitly selects a launch profile that stores a memo seed.

When applying a launch-profile memo seed, Houmao SHALL treat the seed content as caller-authored memo content and SHALL follow the stored memo seed policy for whether existing memo/page content may be written.

Houmao SHALL NOT insert, update, remove, preserve, or interpret generated sections, marker comments, page indexes, headings, metadata blocks, or page links inside `houmao-memo.md`.

#### Scenario: Existing memo is preserved at memory creation
- **WHEN** a managed agent memory root already contains `houmao-memo.md`
- **AND WHEN** Houmao ensures the memory root exists
- **THEN** Houmao leaves the memo content unchanged
- **AND THEN** Houmao does not inspect the memo for generated index markers

#### Scenario: Page mutation does not modify memo
- **WHEN** a caller writes memory page `notes/run.md`
- **THEN** Houmao writes only the contained page under `pages/notes/run.md`
- **AND THEN** it does not append, replace, reformat, or otherwise mutate `houmao-memo.md`

#### Scenario: Launch-profile memo seed is an explicit memo write
- **WHEN** an operator launches from profile `researcher` that stores a memo seed
- **AND WHEN** the memo seed policy allows applying the seed
- **THEN** Houmao writes the seed content to `houmao-memo.md`
- **AND THEN** Houmao treats that write as explicit profile-owned memo initialization rather than as generated memo indexing

### Requirement: Memo links to pages are authored references
References from `houmao-memo.md` to files under `pages/` SHALL be ordinary Markdown content authored by a user or LLM.

Houmao SHALL NOT automatically create page links in `houmao-memo.md`.

Houmao SHALL NOT repair, remove, validate, sort, or regenerate page links in `houmao-memo.md`.

#### Scenario: User-authored page link remains ordinary text
- **WHEN** `houmao-memo.md` contains `[run notes](pages/notes/run.md)`
- **AND WHEN** Houmao lists, writes, appends, or deletes memory pages
- **THEN** the link remains ordinary memo text
- **AND THEN** Houmao does not treat the link as managed metadata

### Requirement: Memory pages expose path-discovery metadata
Houmao SHALL provide a supported way to resolve a page-relative path under `pages/` without requiring that the page already exists.

The page path-resolution response SHALL include:

- the page path relative to `pages/`,
- a relative link string usable from `houmao-memo.md`,
- the absolute filesystem path,
- whether the path currently exists,
- and the existing path kind when available.

The relative link SHALL use the form `pages/<page-relative-path>`.

The absolute filesystem path SHALL be returned only after the input path passes the same containment validation used by page operations.

#### Scenario: Resolve path for a future page
- **WHEN** a caller resolves memory page path `notes/run.md`
- **AND WHEN** the page does not yet exist
- **THEN** Houmao returns `path: notes/run.md`
- **AND THEN** Houmao returns `relative_link: pages/notes/run.md`
- **AND THEN** Houmao returns the absolute path under the managed `pages/` directory
- **AND THEN** Houmao reports that the page does not exist

#### Scenario: Traversal resolve is rejected
- **WHEN** a caller resolves memory page path `../houmao-memo.md`
- **THEN** Houmao rejects the request
- **AND THEN** Houmao does not return an absolute path outside the managed `pages/` directory

### Requirement: Managed memory has no reindex operation
Houmao SHALL NOT expose a supported operation that reindexes pages into `houmao-memo.md`.

Houmao SHALL NOT mutate `houmao-memo.md` as a side effect of page create, write, append, delete, list, read, path resolution, or tree operations.

#### Scenario: Reindex is not a supported memory action
- **WHEN** an operator inspects the supported managed-memory CLI, gateway, or pair-server memory operations
- **THEN** there is no supported reindex action
- **AND THEN** page discovery is available through path, tree, or resolve operations instead

### Requirement: No migration behavior is applied to existing memo content
Houmao SHALL NOT implement migration logic for previous generated memo index content.

Existing content in `houmao-memo.md`, including old generated marker comments or page lists, SHALL be treated as ordinary Markdown.

#### Scenario: Old generated marker block is ignored
- **WHEN** `houmao-memo.md` contains old generated page-index marker comments
- **AND WHEN** Houmao reads the memo or mutates pages
- **THEN** Houmao treats those comments as ordinary memo text
- **AND THEN** Houmao does not remove, refresh, or specially preserve that block

### Requirement: Memo-only launch-profile seeds preserve pages
When applying a launch-profile memo seed that represents only `houmao-memo.md`, Houmao SHALL treat the seed as an explicit memo operation and SHALL NOT inspect, clear, or rewrite the contained `pages/` tree.

Memo-only seeds include inline text seeds, file seeds, and directory seeds that contain `houmao-memo.md` without `pages/`.

#### Scenario: Memo-only replace leaves pages unchanged
- **WHEN** a launch profile stores inline memo seed text with policy `replace`
- **AND WHEN** the target managed memory already contains `pages/notes/start.md`
- **THEN** Houmao replaces `houmao-memo.md` from the seed
- **AND THEN** it leaves `pages/notes/start.md` unchanged

#### Scenario: Empty memo-only replace leaves pages unchanged
- **WHEN** a launch profile stores inline memo seed text `""` with policy `replace`
- **AND WHEN** the target managed memory already contains `pages/notes/start.md`
- **THEN** Houmao writes an empty `houmao-memo.md`
- **AND THEN** it leaves `pages/notes/start.md` unchanged

