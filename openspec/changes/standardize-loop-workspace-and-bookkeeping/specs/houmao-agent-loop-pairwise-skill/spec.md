## ADDED Requirements

### Requirement: Stable pairwise plans include explicit workspace and bookkeeping contracts
The authoring guidance in `houmao-agent-loop-pairwise` SHALL require every authored pairwise loop plan to include a workspace contract and a bookkeeping contract.

When the authored plan uses the standard workspace contract, the plan SHALL identify the selected standard workspace posture, the allowed source-mutation surface, the default read-only shared surfaces, and whether ad hoc worktrees are forbidden or allowed.

When the authored plan uses the standard bookkeeping contract, the plan SHALL identify the required bookkeeping categories, update expectations, and explicit bookkeeping locations for the run.

#### Scenario: Single-file pairwise plan records both contracts
- **WHEN** a user authors a stable pairwise loop plan in single-file form
- **THEN** the final plan records both a workspace contract and a bookkeeping contract
- **AND THEN** those contract sections identify where work and bookkeeping are expected to happen

### Requirement: Stable pairwise guidance does not invent bookkeeping paths or ad hoc worktrees during run control
The operating guidance in `houmao-agent-loop-pairwise` SHALL treat plan-declared workspace and bookkeeping contracts as authoritative for run setup and reporting interpretation.

The guidance SHALL NOT tell participants to create ad hoc worktrees or to improvise bookkeeping locations when the accepted plan has already declared those surfaces.

#### Scenario: Start follows the plan-declared contract
- **WHEN** an operator starts a stable pairwise run whose accepted plan declares explicit workspace and bookkeeping contracts
- **THEN** the guidance points the master at the accepted plan contract
- **AND THEN** it does not replace that contract with improvised worktree or bookkeeping instructions
