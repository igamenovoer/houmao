## MODIFIED Requirements

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
