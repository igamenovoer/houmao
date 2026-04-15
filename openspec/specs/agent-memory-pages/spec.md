# agent-memory-pages Specification

## Purpose
Define the managed-agent memory directory contract centered on one free-form memo file and one contained pages directory.
## Requirements
### Requirement: Managed agents expose one memo-pages memory directory
For each tmux-backed managed agent, Houmao SHALL resolve a per-agent memory root rooted by default at `<active-overlay>/memory/agents/<agent-id>/`.

The memory root SHALL contain a fixed `houmao-memo.md` file and exactly one Houmao-managed subdirectory named `pages/`.

Houmao SHALL create the memory root, `houmao-memo.md`, and `pages/` before a managed launch or join is considered complete.

Houmao SHALL NOT create or publish managed `scratch/` or `persist/` subdirectories as part of the managed-agent memory contract.

#### Scenario: Default memory derives from active overlay and agent id
- **WHEN** managed agent `researcher` has authoritative agent id `researcher-id`
- **AND WHEN** the active overlay resolves as `/repo/.houmao`
- **THEN** the default memory root is `/repo/.houmao/memory/agents/researcher-id/`
- **AND THEN** the default memo file is `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** the default pages directory is `/repo/.houmao/memory/agents/researcher-id/pages/`
- **AND THEN** Houmao does not create `/repo/.houmao/memory/agents/researcher-id/scratch/` or `/repo/.houmao/memory/agents/researcher-id/persist/`

#### Scenario: Memo file is not overwritten
- **WHEN** managed agent `researcher` already has `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND WHEN** Houmao starts, joins, or relaunches that managed agent
- **THEN** Houmao preserves the existing memo file content
- **AND THEN** Houmao does not inspect the memo for generated index markers

### Requirement: Managed memory environment variables use memo-pages names
For every tmux-backed managed session, Houmao SHALL publish `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR` into the live session environment.

Houmao SHALL NOT publish `HOUMAO_AGENT_STATE_DIR`, `HOUMAO_AGENT_SCRATCH_DIR`, or `HOUMAO_AGENT_PERSIST_DIR` as part of the current managed-agent memory contract.

Houmao SHALL NOT publish `HOUMAO_JOB_DIR` or `HOUMAO_MEMORY_DIR` as current managed-agent memory variables.

#### Scenario: Managed session publishes memo-pages variables
- **WHEN** a managed session resolves memory root `/repo/.houmao/memory/agents/researcher-id`
- **THEN** the live environment contains `HOUMAO_AGENT_MEMORY_DIR=/repo/.houmao/memory/agents/researcher-id`
- **AND THEN** the live environment contains `HOUMAO_AGENT_MEMO_FILE=/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** the live environment contains `HOUMAO_AGENT_PAGES_DIR=/repo/.houmao/memory/agents/researcher-id/pages`
- **AND THEN** the live environment does not contain `HOUMAO_AGENT_SCRATCH_DIR`
- **AND THEN** the live environment does not contain `HOUMAO_AGENT_PERSIST_DIR`

### Requirement: Memory page operations are contained under pages
All supported memory page operations SHALL address paths relative to the managed `pages/` directory.

Page operations SHALL reject empty paths, absolute paths, parent traversal, paths that resolve outside `pages/` after symlink resolution, and content containing NUL bytes.

Supported write and append operations SHALL create UTF-8 text page files. Supported page operations SHALL NOT write arbitrary files at the memory root beside `houmao-memo.md`.

#### Scenario: Traversal page path is rejected
- **WHEN** an operator requests memory page path `../houmao-memo.md`
- **THEN** the operation fails before reading or writing any file
- **AND THEN** the failure explains that page paths must stay within the managed pages directory

#### Scenario: Symlink escape is rejected
- **WHEN** the pages directory contains a symlink whose target resolves outside the pages directory
- **AND WHEN** a memory page read request addresses that symlink
- **THEN** Houmao rejects the request
- **AND THEN** Houmao does not read the target outside the pages directory

### Requirement: Houmao exposes supported memory operations through CLI and gateway surfaces
Houmao SHALL provide supported operator entrypoints to resolve memory root paths, read the memo, replace the memo, append to the memo, list pages, resolve page paths, read pages, write pages, append pages, and delete pages.

The live gateway SHALL expose equivalent memo and page operations for attached agents, and the pair server SHALL proxy those operations for managed agents resolved through the server.

The supported surfaces SHALL use memo/page vocabulary and SHALL NOT expose lane-scoped `scratch` or `persist` operations.

Houmao SHALL NOT expose a supported operation that reindexes pages into `houmao-memo.md`.

#### Scenario: CLI resolves memory paths without shelling into the agent
- **WHEN** an operator runs a supported memory path command for managed agent `researcher`
- **THEN** the command reports the memory root, memo file, and pages directory
- **AND THEN** the command does not report scratch or persist lanes

#### Scenario: CLI resolves a memo-friendly page link
- **WHEN** an operator runs a supported memory resolve command for page `loop-contexts/run-1.md`
- **THEN** the command returns `path: loop-contexts/run-1.md`
- **AND THEN** it returns `relative_link: pages/loop-contexts/run-1.md`
- **AND THEN** it returns an absolute path under the managed pages directory

#### Scenario: Gateway appends to the agent memo
- **WHEN** an attached gateway receives a request to append initialization rules to the memo
- **THEN** the gateway appends that content to `<memory-root>/houmao-memo.md`
- **AND THEN** the request cannot redirect the append to another memory-root file

### Requirement: Managed launches cue agents to consult the fixed memo
For every tmux-backed managed launch or join that renders the default managed prompt header, Houmao SHALL provide agent-facing prompt guidance that identifies the fixed `houmao-memo.md` file as durable per-agent context.

That guidance SHALL include the resolved absolute memo file path for the launched or joined managed agent.

That guidance SHALL instruct the agent to read `houmao-memo.md` at the start of each prompt turn before planning or acting.

That guidance SHALL treat files under `pages/` as supporting material reached through authored memo links or explicit task context, not as an automatically indexed memory database.

#### Scenario: Managed launch identifies the memo path in prompt guidance
- **WHEN** managed agent `researcher` launches with memo file `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND WHEN** the managed prompt header renders the memo cue section
- **THEN** the prompt guidance includes `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** it tells the agent to read that file at the start of each prompt turn before planning or acting

#### Scenario: Memo cue preserves the pages-as-authored-links model
- **WHEN** the memo cue mentions supporting pages
- **THEN** it directs the agent to follow relevant authored links under `pages/` when needed
- **AND THEN** it does not describe pages as an automatically generated memo index

