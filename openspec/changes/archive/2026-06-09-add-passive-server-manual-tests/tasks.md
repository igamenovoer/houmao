## 1. Shared Manual-Test Harness

- [x] 1.1 Add small reusable helpers inside the manual scripts for free-port selection, JSON HTTP requests, subprocess startup/readiness polling, and clear failure messages.
- [x] 1.2 Ensure each script creates isolated temporary Houmao roots and passes `HOUMAO_GLOBAL_RUNTIME_DIR`, `HOUMAO_GLOBAL_REGISTRY_DIR`, `HOUMAO_GLOBAL_MAILBOX_DIR`, and `HOUMAO_LOCAL_JOBS_DIR` to child processes.
- [x] 1.3 Ensure each script cleans up owned subprocesses, fake servers, temporary directories, and tmux sessions in `finally` paths.

## 2. Lifecycle Script

- [x] 2.1 Create `tests/manual/manual_passive_server_http_lifecycle.py`.
- [x] 2.2 Start `pixi run houmao-passive-server serve` on a free local port and wait until `/health` responds.
- [x] 2.3 Assert `/health`, `/houmao/server/current-instance`, and empty `/houmao/agents` JSON payloads contain the expected passive-server fields.
- [x] 2.4 Exercise passive-server shutdown or subprocess termination and print a stable PASS marker on success.

## 3. Registry Discovery Script

- [x] 3.1 Create `tests/manual/manual_passive_server_registry_discovery.py`.
- [x] 3.2 Start a real tmux session and publish a fresh active `ManagedAgentRegistryRecordV3` for that session using existing registry helpers.
- [x] 3.3 Publish or write at least one stale or dead registry record that the passive server must not list.
- [x] 3.4 Assert `GET /houmao/agents` lists only the live record with GUI-relevant summary fields.
- [x] 3.5 Assert resolve-by-id, resolve-by-name, and not-found responses through `GET /houmao/agents/{agent_ref}`.

## 4. Gateway Proxy Script

- [x] 4.1 Create `tests/manual/manual_passive_server_gateway_proxy.py`.
- [x] 4.2 Start a fake local gateway that implements `GET /v1/status` and `POST /v1/requests` with strict JSON responses accepted by passive-server gateway client models.
- [x] 4.3 Publish a live registry record with gateway coordinates pointing to the fake gateway.
- [x] 4.4 Assert passive-server discovery reports `has_gateway: true` for the seeded agent.
- [x] 4.5 Assert passive-server forwards gateway status and `submit_prompt` request payloads through `/houmao/agents/{agent_ref}/gateway` and `/houmao/agents/{agent_ref}/gateway/requests`.

## 5. Verification

- [x] 5.1 Run the three manual scripts locally when tmux is available and record their PASS markers.
- [x] 5.2 Run `pixi run python -m pytest tests/unit/passive_server` to confirm existing passive-server unit coverage still passes.
- [x] 5.3 Run formatting or linting on the added manual scripts.
