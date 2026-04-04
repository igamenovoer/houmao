## ADDED Requirements

### Requirement: No "agentsys" references remain in docs

All files under `docs/` SHALL be swept for stale "agentsys" references. Any occurrences of `agentsys`, `.agentsys`, `AGENTSYS_`, or `agentsys/` SHALL be replaced with the corresponding `houmao` equivalents (`.houmao`, `HOUMAO_`, `houmao/`). The replacement SHALL be reviewed for contextual accuracy — not a blind find-and-replace.

#### Scenario: No agentsys path references in docs

- **WHEN** searching all `.md` files under `docs/` for `agentsys`
- **THEN** zero matches are found

#### Scenario: Replacement uses correct houmao equivalents

- **WHEN** a replaced reference previously said `.agentsys/agents`
- **THEN** the replacement says `.houmao/agents`
- **AND THEN** the surrounding prose accurately describes the current behavior
