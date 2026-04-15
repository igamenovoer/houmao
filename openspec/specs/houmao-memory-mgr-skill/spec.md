# houmao-memory-mgr-skill Specification

## Purpose
TBD - created by archiving change add-managed-agent-memo-cue. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a packaged `houmao-memory-mgr` system skill
The system SHALL package a Houmao-owned system skill named `houmao-memory-mgr` under the maintained system-skill asset root.

That packaged skill SHALL be triggered for user requests that ask to read, edit, add something to, append something to, remove something from, prune, organize, or otherwise manage a Houmao-managed agent memo or memory page, including requests that mention:

- `houmao memo`,
- `agent memo`,
- `houmao-memo.md`,
- `managed memory`,
- memory `pages/`.

The skill SHALL remain concise enough for ordinary per-turn loading and SHALL NOT flatten unrelated runtime, mailbox, gateway, or lifecycle guidance into the memory-management entrypoint.

#### Scenario: Installed skill handles memo editing language
- **WHEN** an agent or operator asks to add a note to the Houmao agent memo
- **THEN** the installed `houmao-memory-mgr` skill is the packaged Houmao-owned guidance for that request
- **AND THEN** the skill routes the caller to managed memo operations rather than unrelated mailbox, gateway, or lifecycle skills

### Requirement: `houmao-memory-mgr` finds current-agent and selected-agent memory paths
The packaged `houmao-memory-mgr` skill SHALL teach the agent how to find the managed memory paths for the current managed agent through these environment variables when they are available:

- `HOUMAO_AGENT_MEMORY_DIR`,
- `HOUMAO_AGENT_MEMO_FILE`,
- `HOUMAO_AGENT_PAGES_DIR`.

For a selected managed agent other than the current one, the skill SHALL route path discovery through the supported `houmao-mgr agents memory path` command or the equivalent supported managed-agent memory service surface when the caller is already operating through pair-managed HTTP or a live gateway.

The skill SHALL treat the fixed memo file as `houmao-memo.md` and the only managed subdirectory as `pages/`.

#### Scenario: Current managed agent uses environment-published memory paths
- **WHEN** a managed agent receives a request to edit its own memo
- **AND WHEN** `HOUMAO_AGENT_MEMO_FILE` and `HOUMAO_AGENT_PAGES_DIR` are present in its environment
- **THEN** the skill tells the agent to use those paths as the current managed-agent memo and pages locations
- **AND THEN** it does not require raw runtime-manifest probing to locate those paths

#### Scenario: Other managed agent uses supported path discovery
- **WHEN** a caller asks to edit the memo for managed agent `researcher`
- **THEN** the skill routes path discovery through `houmao-mgr agents memory path --agent-name researcher` or an equivalent supported memory service surface
- **AND THEN** it does not guess the other agent's memory root from naming conventions alone

### Requirement: `houmao-memory-mgr` edits memo and pages through supported memory operations
The packaged `houmao-memory-mgr` skill SHALL route memo operations through the supported memo read, replace, and append surfaces.

At minimum, the skill SHALL describe these CLI operations:

- `houmao-mgr agents memory memo show`,
- `houmao-mgr agents memory memo set`,
- `houmao-mgr agents memory memo append`.

The skill SHALL route contained page operations through the supported page tree, resolve, read, write, append, and delete surfaces.

At minimum, the skill SHALL describe these CLI operations:

- `houmao-mgr agents memory tree`,
- `houmao-mgr agents memory resolve`,
- `houmao-mgr agents memory read`,
- `houmao-mgr agents memory write`,
- `houmao-mgr agents memory append`,
- `houmao-mgr agents memory delete`.

When removing or revising specific memo content, the skill SHALL instruct the agent to read the current memo, make the smallest requested edit, and replace the memo with the updated content.

#### Scenario: Removing memo content performs a minimal replace
- **WHEN** a user asks to remove one obsolete instruction from the agent memo
- **THEN** the skill tells the agent to read the current memo content
- **AND THEN** the skill tells the agent to remove only the requested content and write the full revised memo back through the supported memo replace operation

#### Scenario: Page editing stays under pages
- **WHEN** a user asks to create or update a supporting memory page
- **THEN** the skill routes the operation through a page-relative path under `pages/`
- **AND THEN** it does not write arbitrary files beside `houmao-memo.md` at the memory root

### Requirement: `houmao-memory-mgr` preserves free-form memo ownership boundaries
The packaged `houmao-memory-mgr` skill SHALL state that `houmao-memo.md` is free-form Markdown owned by the operator and agent.

The skill SHALL state that references from `houmao-memo.md` to files under `pages/` are authored Markdown links such as `pages/notes/todo.md`.

The skill SHALL NOT instruct the agent to create generated page indexes, marker comments, automatic link refreshes, or page taxonomies inside `houmao-memo.md`.

The skill SHALL warn that short-lived retry counters, dedupe databases, mailbox receipts, gateway reminder state, and live supervision state belong in the relevant Houmao runtime, mailbox, gateway, or workflow mechanism rather than in managed memory pages.

#### Scenario: Skill preserves authored page-link model
- **WHEN** an agent uses `houmao-memory-mgr` to add a supporting page and mention it in the memo
- **THEN** the skill treats the memo reference as ordinary authored Markdown
- **AND THEN** it does not tell the agent to run or simulate a generated page reindex operation

### Requirement: `houmao-memory-mgr` explains launch-profile memo seed scope
When the packaged `houmao-memory-mgr` skill guides launch-profile or easy-profile memo seed edits, it SHALL explain that memo seed policies apply only to the managed-memory components represented by the seed source.

The skill SHALL guide memo-only seed requests through `--memo-seed-text` or `--memo-seed-file` without suggesting that policy `replace` clears pages.

The skill SHALL distinguish `--clear-memo-seed`, which removes stored profile seed configuration, from an empty memo seed, which stores empty memo content for future profile-backed launches.

#### Scenario: Skill routes empty memo seed without clearing pages
- **WHEN** a user asks an agent to make a launch profile seed an empty memo on future launches
- **THEN** `houmao-memory-mgr` guides the agent to use `--memo-seed-text '' --memo-seed-policy replace`
- **AND THEN** the skill states that this affects `houmao-memo.md` and leaves pages outside the memo-only seed scope

#### Scenario: Skill removes stored seed only when requested
- **WHEN** a user asks an agent to remove a stored launch-profile memo seed
- **THEN** `houmao-memory-mgr` guides the agent to use `--clear-memo-seed`
- **AND THEN** the skill does not present `--clear-memo-seed` as a way to write an empty `houmao-memo.md`

