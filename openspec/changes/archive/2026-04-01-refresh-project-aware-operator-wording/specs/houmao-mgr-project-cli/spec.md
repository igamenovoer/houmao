## ADDED Requirements

### Requirement: Project command wording distinguishes selected overlays, non-creating resolution, and implicit bootstrap
Maintained `houmao-mgr project ...` help text, failures, and structured payload wording SHALL distinguish among:

- the selected overlay root for the current invocation,
- non-creating resolution that intentionally does not create the selected or would-bootstrap overlay,
- implicit bootstrap that created the selected overlay during the current invocation.

Operator-facing wording for maintained project commands SHALL use `selected overlay root` or `selected project overlay` terminology rather than stale `discovered project overlay` wording when the command resolved an env-selected or explicitly bootstrapped overlay.

#### Scenario: Non-creating project inspection reports the selected or would-bootstrap overlay
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs a maintained non-creating `houmao-mgr project ...` inspection or removal command
- **THEN** the failure explains which overlay root was selected or would be bootstrapped for that invocation
- **AND THEN** the failure states that the command remained non-creating instead of implying a discovery failure under a different root

#### Scenario: Project-aware bootstrap result surfaces the created overlay explicitly
- **WHEN** a maintained stateful `houmao-mgr project ...` command bootstraps the selected overlay during the current invocation
- **THEN** the resulting operator-facing text or payload identifies the selected overlay root that was created
- **AND THEN** the result does not require the operator to infer that bootstrap solely from later filesystem state
