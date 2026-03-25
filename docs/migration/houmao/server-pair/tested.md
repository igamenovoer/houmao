# What We Tested

This implementation does not claim unlimited CAO parity. The verification boundary is explicit:

- CAO-compatible `/cao/*` HTTP routes are tested as request-surface and local-dispatch contracts owned by `houmao-server`
- retired `houmao-mgr cao ...` and top-level `houmao-mgr launch` surfaces are no longer part of the supported CLI verification boundary
- Houmao-owned server, managed-agent, gateway, and native-selector launch behavior are tested directly for correctness

## Compatibility Source Of Truth

Pinned upstream CAO source used as the compatibility oracle:

- repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- commit: `0fb3e5196570586593736a21262996ca622f53b6`
- tracked checkout: `extern/tracked/cli-agent-orchestrator`

## HTTP Verification

Server-side verification covers the contract Houmao owns at the HTTP boundary.

Verified areas:

- pinned upstream CAO route inventory matches Houmao's CAO-compatible route inventory
- request query-shape parity for preserved compatibility routes such as:
  - `POST /cao/sessions`
  - `GET /cao/terminals/{terminal_id}/output`
  - `GET /cao/terminals/{terminal_id}/inbox/messages`
- local dispatch and route-side hook behavior for:
  - required and optional params
  - path-segment percent encoding
  - created-terminal sync
  - deleted-session and deleted-terminal handling
  - prompt-submission bookkeeping
- Houmao-owned server behavior:
  - root `/health` identity fields without `child_cao`
  - current-instance payload without child metadata
  - session-backed native-selector projection for compatibility startup
  - compatibility registry persistence and shutdown behavior
  - terminal history ordering and limiting

Primary test files:

- [`tests/unit/server/test_app_contracts.py`](../../../tests/unit/server/test_app_contracts.py)
- [`tests/unit/server/test_service.py`](../../../tests/unit/server/test_service.py)

## CLI Verification

CLI-side verification covers the contract Houmao owns at the `houmao-mgr` boundary.

Verified areas:

- root help and supported top-level inventory for:
  - `server`
  - `agents`
  - `brains`
  - `admin`
- `server` lifecycle and session-management behavior for:
  - `server start`
  - `server status`
  - `server stop`
  - `server sessions list`
  - `server sessions show`
  - `server sessions shutdown`
- `agents` behavior for:
  - `agents launch`
  - `agents gateway attach <agent-ref> --port <public-port>`
  - `agents gateway attach` current-session resolution from tmux-published gateway metadata
  - `agents prompt`, `agents mail ...`, and `agents turn ...`
- `brains build`
- `admin cleanup-registry`

Primary test file:

- [`tests/unit/srv_ctrl/test_commands.py`](../../../tests/unit/srv_ctrl/test_commands.py)

## Runtime And Pair Seam Verification

The change also keeps focused coverage around the preserved `houmao_server_rest` runtime seam and the pair-specific startup hooks that no longer require raw `cao-server` assumptions.

Representative file:

- [`tests/unit/agents/realm_controller/test_cao_client_and_profile.py`](../../../tests/unit/agents/realm_controller/test_cao_client_and_profile.py)

## Commands Run

Focused verification run for the absorbed control plane:

```bash
pixi run python -m pytest tests/unit/agents/realm_controller/test_cao_client_and_profile.py -q
```

Result:

- `42 passed in 10.56s`

Focused regression verification run after updating the server and CLI compatibility expectations:

```bash
pixi run python -m pytest tests/unit/server/test_app_contracts.py tests/unit/server/test_service.py tests/unit/srv_ctrl/test_commands.py -q
```

Result:

- `57 passed in 1.42s`

## What We Did Not Claim

The current verification intentionally does not claim:

- full downstream re-testing of every CAO business behavior beyond the supported Houmao-owned boundary
- byte-for-byte human-prose stdout or stderr parity for compatibility commands
- support for mixed pairs such as `houmao-server + cao` or `cao-server + houmao-mgr`

Those omissions are deliberate. They match the implemented boundary and avoid over-claiming behavior outside the supported pair.
