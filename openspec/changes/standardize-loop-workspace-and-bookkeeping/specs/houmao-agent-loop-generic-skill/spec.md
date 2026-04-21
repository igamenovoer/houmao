## ADDED Requirements

### Requirement: Generic loop plans include explicit workspace and bookkeeping contracts
The authoring guidance in `houmao-agent-loop-generic` SHALL require every authored generic loop plan to include a workspace contract and a bookkeeping contract.

When the plan uses the standard workspace contract, it SHALL identify the selected standard workspace posture, mutation surfaces for relevant components, shared read-only surfaces, and ad hoc worktree posture.

When the plan uses the standard bookkeeping contract, it SHALL identify the bookkeeping categories, ownership and visibility posture, update expectations, and explicit bookkeeping locations.

#### Scenario: Generic plan records workspace and bookkeeping contract
- **WHEN** a user authors a generic loop plan with pairwise and relay components
- **THEN** the final plan records a workspace contract and a bookkeeping contract
- **AND THEN** the plan does not leave work or bookkeeping locations to agent improvisation

### Requirement: Generic run control preserves the authored contract
The operating guidance in `houmao-agent-loop-generic` SHALL treat the authored workspace and bookkeeping contracts as part of the accepted run contract.

The guidance SHALL NOT tell the root owner or downstream participants to create ad hoc worktrees or choose opportunistic bookkeeping paths when the accepted plan already defines those concerns.

#### Scenario: Generic start uses the authored contract
- **WHEN** an operator starts a generic loop run whose accepted plan declares workspace and bookkeeping contracts
- **THEN** the root owner receives a run contract that includes those declarations
- **AND THEN** the guidance does not replace them with improvised workspace or bookkeeping instructions
