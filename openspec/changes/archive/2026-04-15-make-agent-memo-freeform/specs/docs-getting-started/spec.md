## ADDED Requirements

### Requirement: Getting-started docs describe free-form managed memo
Getting-started documentation SHALL describe `houmao-memo.md` as a free-form Markdown file edited by users or LLMs.

The documentation SHALL state that Houmao does not generate, refresh, or reindex page links inside `houmao-memo.md`.

The documentation SHALL explain that links from the memo to `pages/...` are authored references.

#### Scenario: Reader understands memo ownership
- **WHEN** a new user reads the managed memory getting-started page
- **THEN** the page explains that `houmao-memo.md` is free-form Markdown
- **AND THEN** the page does not describe a Houmao-generated page index

### Requirement: Getting-started docs explain path discovery
Getting-started documentation SHALL explain how to discover memory root, memo file, pages directory, and contained page full paths.

The documentation SHALL show a supported way to obtain a memo-friendly relative link for a page under `pages/`.

#### Scenario: Reader can link a page manually
- **WHEN** a new user wants to reference `pages/notes/run.md` from `houmao-memo.md`
- **THEN** the getting-started docs show that the user or LLM may add a normal Markdown link to `pages/notes/run.md`
- **AND THEN** the docs show how to obtain the page's full path through the memory interface
