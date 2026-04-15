## ADDED Requirements

### Requirement: Getting-started memory docs explain memo cue and memory-management skill
The getting-started managed-memory documentation SHALL explain that managed launches render a default memo cue in the managed prompt header.

That documentation SHALL state that the memo cue includes the resolved absolute path to `houmao-memo.md` and instructs the agent to read that memo at the start of each prompt turn before planning or acting.

That documentation SHALL explain that `houmao-memory-mgr` is the packaged system skill for agent-facing requests to read, edit, add to, remove from, or organize the managed memo and contained pages.

That documentation SHALL preserve the existing memory model:

- `houmao-memo.md` is free-form Markdown,
- `pages/` contains authored supporting files,
- page links in the memo are authored references,
- Houmao does not generate or refresh memo indexes.

#### Scenario: Reader sees how managed agents are cued to use the memo
- **WHEN** a reader opens the managed-memory getting-started page
- **THEN** the page explains that the managed prompt header includes a default memo cue
- **AND THEN** the page states that the cue identifies the absolute memo path and tells agents to read it at the start of each prompt turn

#### Scenario: Reader sees the packaged skill for memo edits
- **WHEN** a reader wants an agent to add something to or remove something from its Houmao memo
- **THEN** the getting-started docs identify `houmao-memory-mgr` as the packaged system skill for that request
- **AND THEN** the docs keep the memo and pages model free-form rather than describing generated indexes

