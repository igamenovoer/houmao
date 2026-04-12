## MODIFIED Requirements

### Requirement: System Skills section lists every shipped skill with its purpose

The System Skills table in README.md SHALL list `houmao-specialist-mgr` with a description that includes the "set" (edit/patch) verb alongside create, list, inspect, remove, launch, and stop.

#### Scenario: Reader sees specialist editing in the skill table

- **WHEN** a reader scans the System Skills table in README.md
- **THEN** the `houmao-specialist-mgr` row includes "set" in its verb list
