## ADDED Requirements

### Requirement: Memo seed pages stay contained under pages
When applying a directory memo seed, Houmao SHALL write seeded page files only under the resolved managed `pages/` directory.

Memo seed page paths SHALL follow the same containment rules as supported memory page operations: they SHALL reject absolute paths, parent traversal, symlink escapes, and content containing NUL bytes.

A directory memo seed SHALL NOT write arbitrary files beside `houmao-memo.md` at the managed-agent memo root.

#### Scenario: Directory memo seed writes contained pages
- **WHEN** a memo seed directory contains `pages/notes/start.md`
- **AND WHEN** the selected launch profile applies that seed
- **THEN** Houmao writes the page under the target agent's resolved `pages/notes/start.md`
- **AND THEN** it does not modify files outside the managed `pages/` directory

#### Scenario: Directory memo seed rejects traversal
- **WHEN** a memo seed directory contains a page path that would resolve outside `pages/`
- **THEN** Houmao rejects the seed before provider startup
- **AND THEN** it does not copy any seed content into the target memo root

#### Scenario: Directory memo seed rejects symlinks
- **WHEN** a memo seed directory contains a symlink under `pages/`
- **THEN** Houmao rejects the seed before provider startup
- **AND THEN** it reports that memo seed pages must be regular contained files or directories
