## Purpose
Define the retirement contract for the standalone CAO launcher surfaces.

## Requirements

### Requirement: Retired launcher surfaces fail with migration guidance
The repository SHALL retire the standalone CAO launcher surface.

Invoking `houmao-cao-server` or equivalent launcher module entrypoints SHALL fail fast with an explicit error stating that standalone CAO launcher support has been removed from the supported product path and directing the operator to `houmao-server` plus `houmao-mgr`.

That failure SHALL occur before reading launcher config, spawning processes, or mutating launcher artifact state.

#### Scenario: Invoking `houmao-cao-server` returns migration guidance
- **WHEN** an operator invokes `houmao-cao-server start`
- **THEN** the command exits non-zero with explicit migration guidance to `houmao-server` and `houmao-mgr`
- **AND THEN** it does not start or stop any standalone `cao-server` process
