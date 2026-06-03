## Purpose
Define the public `houmao-server` contract as the Houmao-owned CAO-compatible HTTP authority and its additive extension routes over the native compatibility control core.

## Requirements

### Requirement: Retained `houmao.server` modules are internal implementation support only
Retained Python modules under `houmao.server` SHALL be treated as internal implementation support rather than as proof of a maintained standalone server product.

The repository MAY retain Python modules under `houmao.server` when maintained surfaces still use their models, clients, stores, parser adapters, process helpers, tmux helpers, or compatibility utilities.

Retaining those modules SHALL NOT expose or imply a maintained packaged `houmao-server` executable, standalone FastAPI application, `/cao/*` compatibility server, old-server CLI, or public old-server route contract.

Maintained code SHOULD move broadly shared old-server helpers to neutral packages in later cleanup changes when that move reduces coupling without blocking the executable retirement.

#### Scenario: Passive-server imports old-server models during transition
- **WHEN** `houmao-passive-server` imports a model or helper that still lives under `houmao.server`
- **THEN** that import remains an allowed internal implementation detail
- **AND THEN** packaging and active docs still do not expose standalone `houmao-server` as a supported executable

#### Scenario: Old server application routes are not public contract
- **WHEN** an implementation leaves an old FastAPI app module in the tree temporarily
- **THEN** tests and docs do not treat its `/cao/*` or `/houmao/*` routes as maintained public API
- **AND THEN** maintained API coverage belongs to `houmao-passive-server`
