# writer-team-example Specification

## Purpose
TBD - created by archiving change add-writer-team-example. Update Purpose after archive.
## Requirements
### Requirement: Repository includes a writer-team example template

The repository SHALL include a checked-in `examples/writer-team/` example that provides source material for a three-agent story-writing team without committing live Houmao project state.

The example SHALL include, at minimum:

- `README.md`,
- prompt files for `story-writer`, `character-designer`, and `story-reviewer`,
- a pairwise loop plan,
- a start charter template,
- placeholder output directories for chapters, character profiles, and reviews,
- ignore rules for generated runtime and story output.

The example SHALL NOT commit `.houmao/` runtime state, mailbox contents, credentials, generated story chapters, generated character profiles, generated reviews, or machine-specific absolute paths.

#### Scenario: Reader inspects the example tree

- **WHEN** a reader opens `examples/writer-team/`
- **THEN** they find the reusable prompts, loop plan, start charter, README instructions, and story artifact directory placeholders
- **AND THEN** they do not find committed live `.houmao/` state, credentials, mailbox messages, or generated story output

### Requirement: Writer-team prompts define the three-agent roles

The writer-team example SHALL provide role prompts for:

- `story-writer`, the master agent that drafts chapters, asks workers for assistance, revises chapters, and owns run progress,
- `character-designer`, the worker agent that creates or updates character profiles and relationship notes,
- `story-reviewer`, the worker agent that reviews chapters for logic, causality, character plausibility, pacing, and worldbuilding consistency.

The prompts SHALL be reusable as system-prompt files for `houmao-mgr project easy specialist create`.

#### Scenario: User creates specialists from prompt files

- **WHEN** a user follows the example setup instructions
- **THEN** each of the three prompt files can be passed to `houmao-mgr project easy specialist create`
- **AND THEN** the resulting specialists have distinct writer, character-designer, and reviewer responsibilities

### Requirement: Writer-team setup uses supported project easy commands

The writer-team README SHALL show how to materialize the example with supported `houmao-mgr` project/easy commands.

The setup instructions SHALL cover:

- initializing a Houmao project in the example directory,
- creating the three specialists from the prompt files,
- creating reusable easy profiles for `alex-story`, `alex-char`, and `alex-review`,
- configuring filesystem mailbox defaults for the profiles,
- launching the three agents from those profiles,
- starting the loop by delivering a start charter to the master agent.

The README SHALL treat credentials and auth profiles as operator-provided local setup and SHALL NOT include secret material.

#### Scenario: User follows the setup path

- **WHEN** a user follows the writer-team README from a clean checkout
- **THEN** they can initialize local project state, create the three specialists, create launch profiles, and launch the three named agents using supported CLI surfaces
- **AND THEN** no committed credential or runtime artifact is required from the repository

### Requirement: Writer-team loop plan is pairwise and master-owned

The writer-team loop plan SHALL designate one master agent and two named worker agents:

- master: `alex-story`,
- character worker: `alex-char`,
- review worker: `alex-review`.

The loop plan SHALL describe a chapter pipeline in which the master drafts a chapter, delegates character work to the character worker, revises the draft, delegates review to the review worker, addresses review findings, and advances to the next chapter until the requested chapter count is complete.

The loop plan SHALL keep the user outside the execution loop and SHALL require worker results to close back to the master.

#### Scenario: Master runs one chapter cycle

- **WHEN** `alex-story` starts a chapter cycle from the writer-team loop plan
- **THEN** it writes or updates a chapter draft, asks `alex-char` for character-profile work, revises the draft, asks `alex-review` for review, addresses review findings, and records the finalized chapter before advancing

### Requirement: Writer-team artifacts use relative workspace paths

The writer-team loop plan and README SHALL use paths relative to `examples/writer-team/` for generated writing artifacts.

The canonical output paths SHALL be:

- `story/chapters/` for chapter drafts and finalized chapters,
- `story/characters/` for character profiles and relationship notes,
- `story/review/` for review reports,
- `story/run-state.md` for optional master-owned run status.

The example SHALL NOT use absolute paths copied from another workspace.

#### Scenario: User copies the example directory

- **WHEN** a user copies `examples/writer-team/` to another location and follows the README
- **THEN** generated story artifacts are written under that copied directory's `story/` tree
- **AND THEN** the loop plan does not refer back to the original repository checkout or to `../agentsys2`

### Requirement: Writer-team example aligns with managed memory defaults

The writer-team example SHALL NOT configure legacy memory fields such as `memory_binding` or `memory_dir`.

The example SHALL treat `story/` as the user-designated artifact workspace and SHALL leave Houmao-managed agent memory to the normal launch-time environment and project overlay behavior.

#### Scenario: Reader checks memory setup

- **WHEN** a reader reviews the writer-team README, profiles, and loop plan
- **THEN** they do not find manual legacy memory binding configuration
- **AND THEN** they understand that story artifacts are persisted in `story/` while agent memory remains managed by Houmao

