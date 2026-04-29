## ADDED Requirements

### Requirement: Standalone CAO launcher surface is absent
The distribution SHALL NOT expose the standalone CAO launcher as a packaged console script or maintained module entrypoint.

The source tree SHALL NOT maintain a detached `cao-server` launcher implementation for operator use. Supported server startup SHALL be through `houmao-server`, `houmao-passive-server`, and `houmao-mgr server` commands.

#### Scenario: Packaged scripts omit standalone CAO launcher
- **WHEN** the project package metadata is inspected
- **THEN** the script table contains `houmao-server` and `houmao-passive-server`
- **AND THEN** the script table does not contain `houmao-cao-server`

#### Scenario: Standalone launcher module is not maintained
- **WHEN** maintainers inspect maintained runtime launcher modules
- **THEN** there is no supported `houmao.cao.tools.cao_server_launcher` command module
- **AND THEN** there is no supported `houmao.cao.server_launcher` detached process lifecycle implementation

## REMOVED Requirements

### Requirement: Retired launcher surfaces fail with migration guidance
**Reason**: The project is removing the standalone CAO server launcher surface entirely, so retaining executable shims now conflicts with the smaller retained server contract.

**Migration**: Operators SHALL use `houmao-mgr server start`, `houmao-server serve`, or `houmao-passive-server serve` depending on whether they need the active pair server or the registry-first passive server.

#### Scenario: Historical migration shim is no longer required
- **WHEN** an operator needs to start a Houmao server
- **THEN** the supported commands are `houmao-server`, `houmao-passive-server`, or `houmao-mgr server`
- **AND THEN** the system does not preserve `houmao-cao-server` solely to print migration guidance
