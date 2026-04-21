## ADDED Requirements

### Requirement: Pairwise-v2 plans and prestart guidance include workspace and bookkeeping contracts
The authoring guidance in `houmao-agent-loop-pairwise-v2` SHALL require the authored run contract to include a workspace contract and a bookkeeping contract.

For bundle plans, the canonical authored material SHALL record those contracts in the plan-facing surfaces that participants and operators inspect before `start`.

When the plan uses the standard workspace contract, the guidance SHALL identify the selected standard workspace posture, source-mutation surface, read-only shared surfaces, and ad hoc worktree posture.

When the plan uses the standard bookkeeping contract, the guidance SHALL identify the required bookkeeping categories, update expectations, and explicit bookkeeping locations for the run.

#### Scenario: Bundle v2 plan records both contracts before initialize
- **WHEN** a user authors a pairwise-v2 bundle plan
- **THEN** the authored plan records a workspace contract and a bookkeeping contract before the run enters `initialize`
- **AND THEN** those contract sections identify the declared work and bookkeeping surfaces for the run

### Requirement: Pairwise-v2 initialize and start preserve declared bookkeeping surfaces without turning managed memory into bookkeeping state
The `initialize` and `start` guidance in `houmao-agent-loop-pairwise-v2` SHALL preserve the accepted workspace and bookkeeping contracts when preparing participant-facing run material.

The participant initialize material and start-charter material MAY point participants at the declared bookkeeping locations, but SHALL NOT redefine managed memory pages or memo blocks as the primary home for mutable bookkeeping state.

The guidance SHALL NOT invent a fixed subtree under per-agent `kb/` when the accepted plan already declares bookkeeping locations.

#### Scenario: Initialize points at declared bookkeeping locations
- **WHEN** pairwise-v2 initializes a participant for a run whose accepted plan declares bookkeeping paths
- **THEN** the initialize material may reference those declared paths
- **AND THEN** it does not tell the participant to create a new bookkeeping ledger under a fixed Houmao-owned subtree

#### Scenario: Start keeps bookkeeping outside managed memory ledgers
- **WHEN** pairwise-v2 writes participant-facing start material for a run with explicit bookkeeping paths
- **THEN** the material keeps managed memory focused on run guidance and references
- **AND THEN** it does not redefine the memo or managed pages as the mutable bookkeeping ledger for that run
