## REMOVED Requirements

### Requirement: `houmao-mgr server` group exposes server lifecycle commands

**Reason**: `houmao-mgr` no longer owns a maintained lifecycle wrapper for the retired standalone `houmao-server` executable.

**Migration**: Use `houmao-passive-server serve` to run the maintained server API surface. Keep `houmao-mgr` focused on local project, managed-agent, mailbox, credential, cleanup, and system-skill workflows.

### Requirement: `houmao-mgr server sessions` subgroup exposes session management

**Reason**: Old server-owned session management is no longer a maintained manager command surface.

**Migration**: Use maintained `houmao-mgr agents ...` commands for local managed-agent operations and passive-server routes or compatible manager options for API-backed discovery and management.

### Requirement: `houmao-mgr server stop` gracefully shuts down the server

**Reason**: The manager no longer exposes a top-level server lifecycle group for the retired standalone server.

**Migration**: Stop passive-server through its maintained process manager, foreground process, or supported passive-server API where applicable.

### Requirement: `houmao-mgr server start` resolves the runtime root project-aware by default

**Reason**: `houmao-mgr server start` is removed together with the retired standalone server lifecycle wrapper.

**Migration**: Passive-server startup owns its own runtime-root defaults and documented `serve` options. Project-aware runtime-root behavior for local Houmao workflows remains on the active manager commands that still launch or manage agents.

### Requirement: Server help and startup wording describe project-aware runtime-root selection

**Reason**: The old shared help contract between `houmao-mgr server ...` and `houmao-server ...` no longer applies after both public surfaces are retired.

**Migration**: Document passive-server startup wording on `houmao-passive-server serve`; document project-aware runtime-root selection on retained `houmao-mgr` workflows that actually use it.
