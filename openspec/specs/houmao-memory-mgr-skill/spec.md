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

For the current managed agent when environment paths are unavailable, the skill MAY route path discovery through `houmao-mgr agents self memory path` when the caller is inside the owning managed session.

For a selected managed agent other than the current one, the skill SHALL route path discovery through `houmao-mgr agents single --agent-name <name> memory path` or `houmao-mgr agents single --agent-id <id> memory path`, or through the equivalent supported managed-agent memory service surface when the caller is already operating through pair-managed HTTP or a live gateway.

The skill SHALL treat the fixed memo file as `houmao-memo.md` and the only managed subdirectory as `pages/`.

#### Scenario: Current managed agent uses environment-published memory paths
- **WHEN** a managed agent receives a request to edit its own memo
- **AND WHEN** `HOUMAO_AGENT_MEMO_FILE` and `HOUMAO_AGENT_PAGES_DIR` are present in its environment
- **THEN** the skill tells the agent to use those paths as the current managed-agent memo and pages locations
- **AND THEN** it does not require raw runtime-manifest probing to locate those paths

#### Scenario: Current managed agent may use self memory path
- **WHEN** a managed agent receives a request to inspect its own memory paths
- **AND WHEN** environment-published memory paths are unavailable
- **THEN** the skill may route discovery through `houmao-mgr agents self memory path`
- **AND THEN** it does not use the removed `houmao-mgr agents memory path` shape

#### Scenario: Other managed agent uses selected-agent path discovery
- **WHEN** a caller asks to edit the memo for managed agent `researcher`
- **THEN** the skill routes path discovery through `houmao-mgr agents single --agent-name researcher memory path` or an equivalent supported memory service surface
- **AND THEN** it does not guess the other agent's memory root from naming conventions alone

### Requirement: `houmao-memory-mgr` edits memo and pages through supported memory operations
The packaged `houmao-memory-mgr` skill SHALL route memo operations through the supported memo read, replace, and append surfaces.

For current-session CLI work, the skill SHALL describe memo operations through:

- `houmao-mgr agents self memory memo show`,
- `houmao-mgr agents self memory memo set`,
- `houmao-mgr agents self memory memo append`.

For selected-agent CLI work, the skill SHALL describe the same operations under `houmao-mgr agents single --agent-name <name> memory memo ...` or `houmao-mgr agents single --agent-id <id> memory memo ...`.

The skill SHALL route contained page operations through the supported page tree, resolve, read, write, append, and delete surfaces.

For current-session CLI work, the skill SHALL describe page operations through:

- `houmao-mgr agents self memory tree`,
- `houmao-mgr agents self memory resolve`,
- `houmao-mgr agents self memory read`,
- `houmao-mgr agents self memory write`,
- `houmao-mgr agents self memory append`,
- `houmao-mgr agents self memory delete`.

For selected-agent CLI work, the skill SHALL describe the same operations under `houmao-mgr agents single --agent-name <name> memory ...` or `houmao-mgr agents single --agent-id <id> memory ...`.

When removing or revising specific memo content, the skill SHALL instruct the agent to read the current memo, make the smallest requested edit, and replace the memo with the updated content.

#### Scenario: Removing memo content performs a minimal replace
- **WHEN** a user asks to remove one obsolete instruction from the agent memo
- **THEN** the skill tells the agent to read the current memo content
- **AND THEN** the skill tells the agent to remove only the requested content and write the full revised memo back through the supported memo replace operation

#### Scenario: Page editing stays under pages
- **WHEN** a user asks to create or update a supporting memory page
- **THEN** the skill routes the operation through a page-relative path under `pages/`
- **AND THEN** it does not write arbitrary files beside `houmao-memo.md` at the memory root

#### Scenario: Selected-agent memo append uses scoped command shape
- **WHEN** a user asks to append text to managed agent `researcher`'s memo
- **THEN** the skill may show `houmao-mgr agents single --agent-name researcher memory memo append --content <text>`
- **AND THEN** it does not show the removed `houmao-mgr agents memory memo append --agent-name researcher` shape

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
When the packaged `houmao-memory-mgr` skill guides launch-profile or project-profile memo seed edits, it SHALL explain that memo seed sources define which managed-memory components are replaced.

The skill SHALL guide memo-only seed requests through `--memo-seed-text` or `--memo-seed-file` without suggesting or requiring a memo seed policy.

The skill SHALL distinguish `--clear-memo-seed`, which removes stored profile seed configuration, from an empty memo seed, which stores empty memo content for future profile-backed launches.

#### Scenario: Skill routes empty memo seed without clearing pages
- **WHEN** a user asks an agent to make a launch profile seed an empty memo on future launches
- **THEN** `houmao-memory-mgr` guides the agent to use `--memo-seed-text ''`
- **AND THEN** the skill states that this affects `houmao-memo.md` and leaves pages outside the memo-only seed scope
- **AND THEN** the skill does not tell the agent to use `--memo-seed-policy`

#### Scenario: Skill removes stored seed only when requested
- **WHEN** a user asks an agent to remove a stored launch-profile memo seed
- **THEN** `houmao-memory-mgr` guides the agent to use `--clear-memo-seed`
- **AND THEN** the skill does not present `--clear-memo-seed` as a way to write an empty `houmao-memo.md`

### Requirement: `houmao-memory-mgr` treats profile-owned memo seed edits as maintained profile command fields
The packaged `houmao-memory-mgr` skill SHALL treat memo seed options that are part of project profile or raw launch-profile authoring as fields on the maintained profile create, add, or set commands.

The skill SHALL NOT duplicate profile YAML skeletons or full profile command skeletons only to explain memo seed flags.

The skill SHALL NOT pass memo seed fields to `houmao-mgr internals config-drafts generate`, because initial config drafts accept only minimal name/source/credential holes.

Live memory commands such as memo show/set/append and memory page read/write operations SHALL remain direct skill guidance unless a future change adds a matching maintained config surface for those live commands.

#### Scenario: Profile memo seed authoring uses maintained profile mutation
- **WHEN** a user asks to add memo seed text while creating or updating a profile
- **THEN** the skill guidance routes the profile mutation through the matching maintained profile `create`, `add`, or `set` command field
- **AND THEN** memo seed text/file/dir conflicts are handled by that maintained command path rather than by a config-draft intent

#### Scenario: Live memo append remains skill guidance
- **WHEN** a user asks to append to the live memo of an existing agent
- **THEN** the skill may use the maintained live memory command directly
- **AND THEN** it does not require a profile config-draft generation step
