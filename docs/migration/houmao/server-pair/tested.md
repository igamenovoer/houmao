# What We Tested

This implementation does not claim unlimited CAO parity. The verification boundary is explicit:

- CAO-compatible passthrough HTTP routes are tested as request-surface acceptance and forwarding contracts.
- Delegated `houmao-srv-ctrl` commands are tested as command-surface acceptance and forwarding contracts.
- Houmao-owned extensions and lifecycle behavior are tested directly for correctness.

## Compatibility Source Of Truth

Pinned upstream CAO source used for compatibility verification:

- repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- commit: `0fb3e5196570586593736a21262996ca622f53b6`
- tracked checkout: `extern/tracked/cli-agent-orchestrator`

## HTTP Verification

Server-side verification covers the contract Houmao actually owns at the HTTP boundary.

Verified areas:

- pinned upstream CAO route inventory matches Houmao's CAO-compatible route inventory
- request query-shape parity for compatibility routes such as:
  - `POST /sessions`
  - `GET /terminals/{terminal_id}/output`
  - `GET /terminals/{terminal_id}/inbox/messages`
- request forwarding for:
  - required and optional params
  - path-segment percent encoding
  - additive query handling
- Houmao-owned server behavior:
  - additive `/health` payload
  - current-instance payload
  - launch registration
  - terminal history ordering and limiting
  - startup seeding from child sessions
  - watch-worker startup and shutdown behavior
  - child metadata and derived-port reporting

Primary test files:

- [`tests/unit/server/test_app_contracts.py`](../../../tests/unit/server/test_app_contracts.py)
- [`tests/unit/server/test_service.py`](../../../tests/unit/server/test_service.py)

## CLI Verification

CLI-side verification covers the contract Houmao actually owns at the `houmao-srv-ctrl` boundary.

Verified areas:

- pinned upstream CAO command-family inventory matches `houmao-srv-ctrl`
- delegated argument forwarding for representative passthrough commands:
  - `flow`
  - `init`
  - `install`
  - `mcp-server`
- supported-pair enforcement before forwarding for:
  - `info`
  - `shutdown`
  - `launch`
- Houmao-owned `launch` follow-up behavior:
  - session discovery
  - runtime artifact materialization
  - `houmao-server` registration payload
  - headless additive completion output
  - delegated non-zero exit propagation without false Houmao follow-up

Primary test file:

- [`tests/unit/srv_ctrl/test_commands.py`](../../../tests/unit/srv_ctrl/test_commands.py)

## Runtime And Persisted Contract Coverage

The server-pair work also reuses existing runtime and schema coverage already present in this repository for:

- `houmao_server_rest` manifest persistence
- gateway attach metadata
- shared-registry pointer publication
- runtime backend schema support

Representative files:

- [`tests/unit/agents/realm_controller/test_schema_and_manifest.py`](../../../tests/unit/agents/realm_controller/test_schema_and_manifest.py)
- [`tests/unit/agents/realm_controller/test_gateway_support.py`](../../../tests/unit/agents/realm_controller/test_gateway_support.py)
- [`tests/unit/srv_ctrl/test_runtime_artifacts.py`](../../../tests/unit/srv_ctrl/test_runtime_artifacts.py)

## Commands Run

Focused verification added for this implementation:

```bash
pixi run pytest \
  tests/unit/server/test_app_contracts.py \
  tests/unit/server/test_service.py \
  tests/unit/srv_ctrl/test_commands.py
```

Result:

- `28 passed`

Broader repository validation run after the new verification landed:

```bash
pixi run test
pixi run lint
openspec validate add-houmao-server --strict
```

Results:

- `pixi run test` -> `474 passed`
- `pixi run lint` -> pass
- `openspec validate add-houmao-server --strict` -> pass

## What We Did Not Claim

The current verification intentionally does not claim:

- full downstream re-testing of every CAO business behavior behind passthrough HTTP routes
- byte-for-byte stdout or stderr parity for delegated CLI commands
- support for mixed pairs such as `houmao-server + cao` or `cao-server + houmao-srv-ctrl`

Those omissions are deliberate. They match the implemented boundary and avoid over-claiming behavior that still belongs to the delegated CAO side.
