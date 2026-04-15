## REMOVED Requirements

### Requirement: Gateway exposes lane-scoped managed workspace endpoints
**Reason**: The live gateway no longer exposes lane-scoped workspace operations.

**Migration**: Use gateway memory endpoints for memo and page operations.

### Requirement: Gateway workspace endpoints enforce path containment
**Reason**: Workspace-lane containment is replaced by pages-directory containment.

**Migration**: Gateway memory page endpoints enforce containment under the managed pages directory, and memo endpoints target only the fixed memo file.

## ADDED Requirements

### Requirement: Gateway exposes managed memory memo and page endpoints
The live gateway SHALL expose HTTP endpoints for managed memory inspection and memo/page operations.

The gateway memory surface SHALL include:
- a memory summary endpoint that reports memory root, memo file, and pages directory,
- memo read, replace, and append endpoints for the fixed `houmao-memo.md` file,
- page list, read, write, append, and delete endpoints,
- a memo reindex endpoint that rebuilds the managed pages index from contained pages.

The gateway SHALL NOT expose `scratch` or `persist` lane identifiers on this surface.

#### Scenario: Gateway memory summary reports memo-pages paths
- **WHEN** a live gateway is attached to managed agent `researcher`
- **THEN** the memory summary returns the memory root
- **AND THEN** it returns the memo file path
- **AND THEN** it returns the pages directory
- **AND THEN** it does not return a scratch directory or persist directory

#### Scenario: Gateway rejects lane-style request
- **WHEN** a live gateway receives a workspace lane request for lane `scratch`
- **THEN** the request fails before touching the filesystem
- **AND THEN** the response identifies the lane workspace surface as unsupported

### Requirement: Gateway memory endpoints enforce page containment
Gateway page file operations SHALL accept relative page paths only and SHALL verify that each resolved target remains within the managed pages directory.

Gateway page file operations SHALL reject absolute paths, parent traversal, symlink escapes, and content containing NUL bytes.

Gateway memo operations SHALL operate only on the resolved fixed memo file and SHALL NOT accept arbitrary memory-root target paths.

#### Scenario: Gateway rejects page symlink escape
- **WHEN** the pages directory contains a symlink whose target resolves outside the pages directory
- **AND WHEN** a gateway memory read request addresses that symlink
- **THEN** the gateway rejects the request
- **AND THEN** it does not read the target outside the pages directory

#### Scenario: Gateway page write refreshes memo index
- **WHEN** a gateway memory page write request is accepted for page `operator-rules.md`
- **THEN** the gateway writes to the contained page path
- **AND THEN** it refreshes the managed pages index in `houmao-memo.md`
