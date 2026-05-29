## Why

Houmao's maintained operator path is now `houmao-mgr` for local workflows and `houmao-passive-server` for API-based collection and management of running agents. The legacy `houmao-cli` and standalone `houmao-server` executable surfaces add maintenance burden and documentation ambiguity even though useful Python modules from the old server package may still serve maintained code paths.

## What Changes

- **BREAKING** Remove `houmao-server` from packaged console scripts and stop documenting it as an installable standalone executable.
- **BREAKING** Remove `houmao-cli` from packaged console scripts and retire the public realm-controller compatibility CLI surface.
- **BREAKING** Remove the `houmao-mgr server ...` command group and its old-server lifecycle/session-management commands.
- Reposition `houmao-passive-server` as the only maintained server API surface for discovering, observing, and managing running Houmao agents.
- Retain useful `houmao.server` Python modules as internal implementation or shared support modules when they are still consumed by maintained surfaces such as `houmao-mgr` or `houmao-passive-server`.
- Stop promising the old standalone `houmao-server` HTTP contract, including `/cao/*`, `houmao_server_rest`, and direct old-server CLI documentation, as a maintained operator/API surface.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `repo-identity-guidance`: Update canonical public surfaces to `houmao-mgr` and `houmao-passive-server`; make `houmao-cli` and standalone `houmao-server` historical or internal-only contexts.
- `docs-cli-reference`: Remove `houmao-server` from retained executable/server reference coverage, remove `houmao-cli` from deprecated installed entrypoint guidance, and make passive-server the maintained server API reference.
- `project-cli-identity`: Replace the old `houmao-mgr` plus `houmao-server` operator identity with `houmao-mgr` plus `houmao-passive-server`.
- `houmao-mgr-server-group`: Retire the `houmao-mgr server` command group instead of requiring it.
- `houmao-server`: Retire the standalone executable/server contract while allowing reusable `houmao.server` modules to remain internal.
- `houmao-server-agent-api`: Move maintained managed-agent API ownership from standalone `houmao-server` to `houmao-passive-server`, with old server API behavior no longer promised.
- `passive-server-client-compatibility`: Make passive-server the maintained pair-authority target for manager/API clients and remove active reliance on standalone `houmao-server` as a supported pair authority.
- `brain-launch-runtime`: Retire public `houmao_server_rest` and `houmao-cli` runtime entrypoints while preserving local/headless/runtime helpers used by maintained manager and passive-server flows.

## Impact

- Packaging: `pyproject.toml` console scripts change; `houmao-mgr` and `houmao-passive-server` remain packaged.
- CLI: `houmao-mgr` keeps local agent/project/brain/mailbox/credential/system-skill workflows but no longer exposes `server`.
- Runtime/API: active API management points at `houmao-passive-server`; old `/cao/*` and `houmao_server_rest` surfaces become retired legacy internals or are removed.
- Code organization: useful old-server models, clients, headless-store records, and TUI helpers may remain temporarily under `houmao.server` or move to neutral modules; their package location alone does not imply a supported standalone server product.
- Tests/docs/specs: server executable, old server CLI reference, `houmao-mgr server`, and `houmao-cli` tests/docs need removal or historical rewrite; passive-server and manager tests become the maintained coverage owners.
