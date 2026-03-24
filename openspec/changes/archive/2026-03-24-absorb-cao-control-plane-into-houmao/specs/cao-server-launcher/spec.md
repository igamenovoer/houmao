## ADDED Requirements

### Requirement: Retired launcher surfaces fail with migration guidance
The repository SHALL retire the standalone CAO launcher surface.

Invoking `houmao-cao-server` or equivalent launcher module entrypoints SHALL fail fast with an explicit error stating that standalone CAO launcher support has been removed from the supported product path and directing the operator to `houmao-server` plus `houmao-srv-ctrl`.

That failure SHALL occur before reading launcher config, spawning processes, or mutating launcher artifact state.

#### Scenario: Invoking `houmao-cao-server` returns migration guidance
- **WHEN** an operator invokes `houmao-cao-server start`
- **THEN** the command exits non-zero with explicit migration guidance to `houmao-server` and `houmao-srv-ctrl`
- **AND THEN** it does not start or stop any standalone `cao-server` process

## REMOVED Requirements

### Requirement: Launcher is configured via a server config file
**Reason**: The supported product no longer includes a standalone CAO launcher lifecycle.
**Migration**: Launch and manage the supported pair through `houmao-server` and `houmao-srv-ctrl`; do not provision standalone CAO launcher config files for the supported path.

### Requirement: Launcher config files are schema-validated
**Reason**: Standalone launcher config is no longer part of the supported contract once `houmao-cao-server` is retired.
**Migration**: Move supported server selection and control to the `houmao-server` and `houmao-srv-ctrl` pair instead of maintaining standalone launcher config.

### Requirement: Start (or reuse) a local CAO server
**Reason**: The supported product no longer starts or manages a standalone `cao-server` process through `houmao-cao-server`.
**Migration**: Start `houmao-server` and use `houmao-srv-ctrl` as the supported companion CLI; do not expect `houmao-cao-server start` to bootstrap a standalone CAO service.

### Requirement: Status reports CAO health without side effects
**Reason**: Standalone CAO launcher status is removed with the retired launcher surface.
**Migration**: Use `houmao-server` health and pair-owned control/status surfaces instead of standalone launcher status commands.

### Requirement: Launcher writes pid and log artifacts under the runtime root
**Reason**: Retiring the standalone launcher removes the supported pidfile and launcher-artifact lifecycle.
**Migration**: Use Houmao server runtime artifacts and logs produced by the supported pair rather than launcher-managed `cao-server` pid/log directories.

### Requirement: Stop is pidfile-based with best-effort identity verification
**Reason**: The supported product no longer exposes standalone CAO stop semantics through `houmao-cao-server`.
**Migration**: Stop or recycle the supported pair through `houmao-server` and `houmao-srv-ctrl`; do not depend on launcher pidfile ownership checks.

### Requirement: Launcher stop SHALL persist structured diagnostics from a fresh runtime root
**Reason**: Retiring the launcher removes launcher-owned stop-result artifacts from the supported contract.
**Migration**: Use supported pair diagnostics instead of expecting launcher-specific `stop` result files.

### Requirement: Launcher uses `cao-server` from `PATH`
**Reason**: The supported product path no longer shells out to standalone `cao-server`.
**Migration**: Do not install or target standalone `cao-server` as part of the supported Houmao pair workflow.

### Requirement: Proxy policy is configurable for the launched CAO server process
**Reason**: The supported product no longer launches a standalone CAO server process through the retired launcher surface.
**Migration**: Use the supported pair's proxy and loopback policies on `houmao-server` and pair-owned compatibility clients instead of launcher proxy settings.

### Requirement: Launcher home directory anchors CAO state and process HOME
**Reason**: The supported product no longer exposes a standalone launcher-owned CAO home contract.
**Migration**: Use Houmao-owned profile-store and server runtime roots managed by the supported pair rather than launcher-derived CAO homes.

### Requirement: User-facing launcher CLI uses the Houmao name
**Reason**: `houmao-cao-server` is now a retirement surface rather than a supported launcher command.
**Migration**: Update docs, scripts, and operator workflows to use `houmao-server` and `houmao-srv-ctrl` instead of teaching `houmao-cao-server` as a current launcher.
