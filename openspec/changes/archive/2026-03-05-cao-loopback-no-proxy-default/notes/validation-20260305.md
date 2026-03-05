# Validation Notes (2026-03-05)

Timestamp (UTC): `2026-03-05T07:05:47Z`

## 1) Targeted unit tests

Command:

```bash
pixi run python -m pytest \
  tests/unit/cao/test_no_proxy.py \
  tests/unit/cao/test_server_launcher.py \
  tests/unit/agents/brain_launch_runtime/test_headless_base.py \
  tests/unit/agents/brain_launch_runtime/test_codex_app_server.py \
  tests/unit/agents/brain_launch_runtime/test_cao_client_and_profile.py
```

Result:

- `50 passed` (no failures)

## 2) CAO loopback smoke under proxy-heavy shell env

Precondition:

- Local CAO server reachable at `http://localhost:9889` during this run.

Proxy-heavy env used for each smoke command:

- `HTTP_PROXY=http://127.0.0.1:65535`
- `HTTPS_PROXY=http://127.0.0.1:65535`
- `ALL_PROXY=socks5://127.0.0.1:65535`
- `NO_PROXY` and `no_proxy` unset (`env -u NO_PROXY -u no_proxy`)

### 2.1 Launcher default behavior (injection enabled)

Command:

```bash
env -u NO_PROXY -u no_proxy \
  HTTP_PROXY=http://127.0.0.1:65535 \
  HTTPS_PROXY=http://127.0.0.1:65535 \
  ALL_PROXY=socks5://127.0.0.1:65535 \
  pixi run python -m agent_system_dissect.cao.tools.cao_server_launcher status --config <temp-config>
```

Observed result:

- `healthy=true`
- `health_status="ok"`

### 2.2 Launcher preserve-mode opt-out

Command:

```bash
env -u NO_PROXY -u no_proxy \
  HTTP_PROXY=http://127.0.0.1:65535 \
  HTTPS_PROXY=http://127.0.0.1:65535 \
  ALL_PROXY=socks5://127.0.0.1:65535 \
  AGENTSYS_PRESERVE_NO_PROXY_ENV=1 \
  pixi run python -m agent_system_dissect.cao.tools.cao_server_launcher status --config <temp-config>
```

Observed result:

- `healthy=false`
- error from proxy path (`HTTP 502`)
- CLI exit code: `2`

### 2.3 CAO REST client default behavior (injection enabled)

Command:

```bash
env -u NO_PROXY -u no_proxy \
  HTTP_PROXY=http://127.0.0.1:65535 \
  HTTPS_PROXY=http://127.0.0.1:65535 \
  ALL_PROXY=socks5://127.0.0.1:65535 \
  pixi run python - <<'PY'
from agent_system_dissect.cao.rest_client import CaoRestClient
print(CaoRestClient("http://localhost:9889", timeout_seconds=3.0).health().model_dump())
PY
```

Observed result:

- `{'status': 'ok', 'service': 'cli-agent-orchestrator'}`

### 2.4 CAO REST client preserve-mode opt-out

Command:

```bash
env -u NO_PROXY -u no_proxy \
  HTTP_PROXY=http://127.0.0.1:65535 \
  HTTPS_PROXY=http://127.0.0.1:65535 \
  ALL_PROXY=socks5://127.0.0.1:65535 \
  AGENTSYS_PRESERVE_NO_PROXY_ENV=1 \
  pixi run python - <<'PY'
from agent_system_dissect.cao.rest_client import CaoApiError, CaoRestClient
try:
    CaoRestClient("http://localhost:9889", timeout_seconds=3.0).health()
except CaoApiError as exc:
    print(f"error={exc.detail}")
PY
```

Observed result:

- Request fails under proxy-heavy env when preserve mode is enabled.
- Captured error detail: `empty error response body`.

## Summary

- Default behavior bypasses ambient proxies for loopback CAO paths.
- Preserve mode (`AGENTSYS_PRESERVE_NO_PROXY_ENV=1`) leaves caller proxy/no-proxy behavior intact.
