## Purpose
Define the Houmao-owned managed-agent API for shared managed-agent discovery, transport-neutral read surfaces, and native headless lifecycle control.
## Requirements

### Requirement: Maintained managed-agent API ownership belongs to `houmao-passive-server`
Maintained managed-agent HTTP API behavior SHALL be exposed through `houmao-passive-server` rather than standalone `houmao-server`.

When old server managed-agent models, clients, managed-headless records, or gateway/mail compatibility helpers are still useful, maintained passive-server code MAY import or move those helpers. Their old package location SHALL NOT imply that standalone `houmao-server` remains a maintained API authority.

#### Scenario: Passive-server owns managed-agent API documentation
- **WHEN** docs or tests describe maintained managed-agent HTTP routes
- **THEN** those routes are described as `houmao-passive-server` behavior
- **AND THEN** standalone `houmao-server` route families are not presented as current public API

#### Scenario: Retained models are internal compatibility support
- **WHEN** passive-server reuses response models that still live under `houmao.server.models`
- **THEN** that reuse remains an internal implementation detail
- **AND THEN** the maintained API authority remains `houmao-passive-server`
