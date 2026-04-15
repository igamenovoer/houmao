## ADDED Requirements

### Requirement: Passive server proxies corrected memory path discovery
The passive-server gateway proxy SHALL expose the same managed-memory path-resolution behavior as the live gateway memory API.

The proxy SHALL return page-relative paths, memo-relative link strings, absolute filesystem paths, existence state, and existing path kind when available.

The proxy SHALL preserve gateway containment errors rather than rewriting them as successful path responses.

#### Scenario: Passive proxy resolves a page through the gateway
- **WHEN** a caller asks the passive-server proxy to resolve page path `notes/run.md` for a managed agent
- **AND WHEN** that managed agent has a live gateway
- **THEN** the proxy returns the gateway-provided absolute path and `pages/notes/run.md` relative link

### Requirement: Passive server does not proxy memory reindex
The passive-server gateway proxy SHALL NOT expose a supported memory reindex route or client method.

#### Scenario: Passive proxy memory surface has no reindex route
- **WHEN** a caller inspects the supported passive-server gateway memory proxy routes
- **THEN** no route offers memo page-index rebuilding
