# Spec Delta

## ADDED Requirements

### Requirement: Required runtime startup releases resources on failure
If a managed launch fails before required startup and publication succeed, Houmao SHALL roll back resources acquired for that attempt, withdraw its partial active discovery, and report the launch failure. Cleanup SHALL be scoped to the attempt and its verified execution owner.

#### Scenario: Manifest write fails after the backend starts
- **WHEN** a new managed backend and its observer start but the runtime fails to write the session manifest
- **THEN** Houmao stops the backend and observer resources acquired for that attempt
- **AND THEN** the failed attempt has no live managed discovery record
- **AND THEN** a fresh launch can be attempted after the underlying error is resolved

#### Scenario: Required publication fails after a session manifest is created
- **WHEN** a managed launch writes its manifest but fails to publish required gateway capability or readiness authority
- **THEN** Houmao rolls back the new launch resources and withdraws any partial discovery owned by that generation
- **AND THEN** another generation, preexisting provider resources, operator-owned paths, and the shared tmux server remain intact
- **AND THEN** the result identifies the startup failure and reports any incomplete cleanup

#### Scenario: Optional gateway auto-attach fails after startup
- **WHEN** required startup succeeds and optional launch-time gateway auto-attach subsequently fails
- **THEN** the agent remains live and the result identifies the agent and its gateway-attach failure

#### Scenario: A delegated launch reports an optional gateway failure
- **WHEN** required startup succeeds in a delegated owner and optional gateway auto-attach fails
- **THEN** owner stdio returns a correlated v1 completed result with the live identity and gateway auto-attach error
- **AND THEN** the caller publishes the locator and reports the partial result with the existing local CLI exit status of 2
- **AND THEN** the caller does not repeat the launch
