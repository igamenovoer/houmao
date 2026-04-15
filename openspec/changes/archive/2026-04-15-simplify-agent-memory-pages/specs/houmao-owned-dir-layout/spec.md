## ADDED Requirements

### Requirement: Houmao-owned per-agent memory layout contains memo and pages only
The Houmao-owned per-agent memory root family SHALL remain `<active-overlay>/memory/agents/<agent-id>/`.

For each tmux-backed managed agent, the default managed memory paths SHALL be:
- memo file: `<active-overlay>/memory/agents/<agent-id>/houmao-memo.md`
- pages directory: `<active-overlay>/memory/agents/<agent-id>/pages/`

Houmao SHALL NOT treat `scratch/` or `persist/` under the memory root as current managed layout paths.

#### Scenario: Project-aware local roots resolve memo-pages memory under the active overlay
- **WHEN** active overlay `/repo/.houmao` launches managed agent `researcher-id`
- **THEN** the effective memory root is `/repo/.houmao/memory/agents/researcher-id`
- **AND THEN** the effective memo file is `/repo/.houmao/memory/agents/researcher-id/houmao-memo.md`
- **AND THEN** the effective pages directory is `/repo/.houmao/memory/agents/researcher-id/pages`
- **AND THEN** no managed scratch or persist lane is part of the layout

### Requirement: Managed memory pages remain distinct from artifacts, runtime, and mailbox state
The system SHALL preserve distinct mutability and ownership boundaries across Houmao-owned zones.

The per-agent memory memo file and pages directory SHALL contain small operator-visible notes, instructions, and durable context. Runtime session state, mailbox contents, generated artifacts, downloaded files, and provider-owned internal memory state MUST NOT be relocated into the managed memory root as part of this directory model.

#### Scenario: Work artifacts remain outside managed memory pages
- **WHEN** a managed agent produces task output or downloaded files
- **THEN** those artifacts belong in the launched workdir or an explicit project artifact path
- **AND THEN** managed memory pages may contain a readable pointer or summary
- **AND THEN** the artifacts are not stored in `pages/` by default
