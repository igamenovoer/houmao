## ADDED Requirements

### Requirement: Gateway exposes lane-scoped managed workspace endpoints
The live gateway SHALL expose HTTP endpoints for managed workspace inspection and lane-scoped file operations.

The gateway workspace surface SHALL include:
- a workspace summary endpoint that reports workspace root, scratch directory, persist binding, and persist directory when enabled,
- memo read, replace, and append endpoints for the fixed `houmao-memo.md` file,
- a lane tree endpoint,
- lane file read, write, append, delete endpoints,
- a lane clear endpoint.

The gateway SHALL support only `scratch` and `persist` lane identifiers on this surface.

#### Scenario: Gateway workspace summary reports available lanes
- **WHEN** a live gateway is attached to managed agent `researcher`
- **THEN** `GET /v1/workspace` returns the workspace root
- **AND THEN** it returns the memo file path
- **AND THEN** it returns the scratch directory
- **AND THEN** it returns the persist directory when persistence is enabled

#### Scenario: Gateway rejects unsupported lane
- **WHEN** a live gateway receives a workspace request for lane `runtime`
- **THEN** the request fails before touching the filesystem
- **AND THEN** the response identifies the lane as unsupported

### Requirement: Gateway workspace endpoints enforce path containment
Gateway workspace file operations SHALL accept relative paths only and SHALL verify that each resolved target remains within the selected workspace lane.

Gateway workspace file operations SHALL reject absolute paths, parent traversal, and symlink escapes.

Gateway memo operations SHALL operate only on the resolved fixed memo file and SHALL NOT accept arbitrary root-level target paths.

#### Scenario: Gateway rejects symlink escape
- **WHEN** a scratch lane contains a symlink whose target resolves outside the scratch lane
- **AND WHEN** a gateway workspace read request addresses that symlink
- **THEN** the gateway rejects the request
- **AND THEN** it does not read the target outside the scratch lane

#### Scenario: Gateway memo append uses fixed memo target
- **WHEN** a gateway memo append request is accepted for managed agent `researcher`
- **THEN** the gateway appends to the manifest-backed memo file path
- **AND THEN** the request cannot redirect the append to another workspace-root file
