# Agent Memory Pages Delta

## MODIFIED Requirements

### Requirement: Managed agents expose one memo-pages memory directory
For each tmux-backed managed agent, Houmao SHALL resolve a per-agent memory root rooted by default at `<active-overlay>/memory/agents/<agent-id>/`.

The memory root SHALL contain a fixed `houmao-memo.md` file and exactly one Houmao-managed subdirectory named `pages/`.

Houmao SHALL create the memory root, `houmao-memo.md`, and `pages/` before a managed launch is considered complete.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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
- **AND WHEN** Houmao starts or relaunches that managed agent
- **THEN** Houmao preserves the existing memo file content
- **AND THEN** Houmao does not inspect the memo for generated index markers

### Requirement: Managed launches cue agents to consult the fixed memo
For every tmux-backed managed launch that renders the default managed prompt header, Houmao SHALL provide agent-facing prompt guidance that identifies the fixed `houmao-memo.md` file as durable per-agent context.

That guidance SHALL include the resolved absolute memo file path for the launched managed agent.

That guidance SHALL instruct the agent to read `houmao-memo.md` at the start of each prompt turn before planning or acting.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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
