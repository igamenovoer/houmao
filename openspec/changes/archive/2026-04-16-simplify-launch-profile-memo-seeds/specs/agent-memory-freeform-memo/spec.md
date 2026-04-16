## MODIFIED Requirements

### Requirement: Managed memory memo is free-form caller-owned Markdown
For each managed-agent memory root, Houmao SHALL treat `houmao-memo.md` as free-form Markdown owned by users and LLMs.

Houmao SHALL create `houmao-memo.md` when missing.

Houmao SHALL read, replace, or append `houmao-memo.md` only when the caller explicitly invokes a memo read, replace, or append operation, or when the caller explicitly selects a launch profile that stores a memo seed.

When applying a launch-profile memo seed that represents `houmao-memo.md`, Houmao SHALL treat the seed content as caller-authored memo content and SHALL replace `houmao-memo.md` before provider startup.

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
- **WHEN** an operator launches from profile `researcher` that stores a memo seed representing `houmao-memo.md`
- **THEN** Houmao writes the seed content to `houmao-memo.md`
- **AND THEN** Houmao treats that write as explicit profile-owned memo initialization rather than as generated memo indexing

### Requirement: Memo-only launch-profile seeds preserve pages
When applying a launch-profile memo seed that represents only `houmao-memo.md`, Houmao SHALL treat the seed as an explicit memo operation and SHALL NOT inspect, clear, or rewrite the contained `pages/` tree.

Memo-only seeds include inline text seeds, file seeds, and directory seeds that contain `houmao-memo.md` without `pages/`.

#### Scenario: Memo-only seed leaves pages unchanged
- **WHEN** a launch profile stores inline memo seed text
- **AND WHEN** the target managed memory already contains `pages/notes/start.md`
- **THEN** Houmao replaces `houmao-memo.md` from the seed
- **AND THEN** it leaves `pages/notes/start.md` unchanged

#### Scenario: Empty memo-only seed leaves pages unchanged
- **WHEN** a launch profile stores inline memo seed text `""`
- **AND WHEN** the target managed memory already contains `pages/notes/start.md`
- **THEN** Houmao writes an empty `houmao-memo.md`
- **AND THEN** it leaves `pages/notes/start.md` unchanged
