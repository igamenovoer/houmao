## ADDED Requirements

### Requirement: Registry reference documents external communication-only records
The shared-registry reference documentation SHALL describe external communication-only managed-agent records alongside local lifecycle-managed records.

The documentation SHALL explain:
- why external records are stored separately from local lifecycle records,
- the external record path and schema fields,
- that external records are durable communication locators rather than local runtime authorities,
- how registration, verification, selector resolution, and removal interact with external records,
- why stale local tmux cleanup and local lifecycle transitions do not apply to external records.

#### Scenario: Reader can distinguish external and local registry records
- **WHEN** a reader opens the registry contract documentation
- **THEN** the documentation describes both local lifecycle records and external communication-only records
- **AND THEN** it explains that local lifecycle records own manifest/tmux/runtime locators while external records own only remote communication locators

#### Scenario: Reader understands external cleanup semantics
- **WHEN** a reader checks registry cleanup behavior
- **THEN** the documentation states that local stale-tmux cleanup does not delete valid external communication-only records
- **AND THEN** it points readers to `houmao-mgr agents external remove` for deleting a local external import
