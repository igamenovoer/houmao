## MODIFIED Requirements

### Requirement: houmao-passive-server reference rewritten with operational depth

The CLI reference page `docs/reference/cli/houmao-passive-server.md` SHALL be rewritten from the current stub to a comprehensive reference covering:

- when to use passive-server as the maintained server API surface,
- the registry-driven discovery and observation model,
- passive-server as a global service over the shared registry rather than a Houmao project-bound command,
- the route families and capabilities available through the passive-server REST API,
- operational guidance for starting, configuring, and using passive-server in distributed agent coordination setups,
- the `serve` command with all current options,
- runtime-root and registry-root resolution, including `--runtime-root`, `--registry-root`, `HOUMAO_GLOBAL_RUNTIME_DIR`, `HOUMAO_GLOBAL_REGISTRY_DIR`, and global defaults,
- which `houmao-mgr` commands can target passive-server through supported pair-authority options.

The page SHALL NOT instruct users to choose standalone `houmao-server` as a maintained alternative.

The page SHALL NOT state that a Houmao project overlay is required to start `houmao-passive-server serve`.

#### Scenario: Reader understands when to use passive-server
- **WHEN** a reader opens the `houmao-passive-server` reference
- **THEN** they find guidance that positions passive-server as the maintained server API surface
- **AND THEN** they are not asked to choose between two maintained Houmao server executables

#### Scenario: passive-server API surface documented
- **WHEN** a reader needs to integrate with the passive-server
- **THEN** the page documents the available REST routes and their response contracts
- **AND THEN** the page notes which `houmao-mgr` commands are compatible with the passive-server

#### Scenario: Reader understands global-service root configuration
- **WHEN** a reader opens the `houmao-passive-server` reference
- **THEN** the page explains that `houmao-passive-server serve` can start without a Houmao project overlay
- **AND THEN** the page explains how to use `--registry-root` or `HOUMAO_GLOBAL_REGISTRY_DIR` when CI or tests need an isolated shared registry
