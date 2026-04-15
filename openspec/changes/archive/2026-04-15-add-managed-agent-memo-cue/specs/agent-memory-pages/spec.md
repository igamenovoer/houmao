## ADDED Requirements

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

