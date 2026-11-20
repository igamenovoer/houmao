# Manager and HTTPS Verification

The scoped `gateway web-entry` tests verified explicit enrolled-admin selection, direct owner-local transport, and the exact `url` and `expires_at_utc` output fields in plain and JSON styles. They covered detached gateways, wrong run modes, missing or refused signers, and pair, executor, and nonlocal selections. The client tests sent real request-bound SSHSIG proof with an empty issuance body. A redirect, native URL response, or proof refusal produced a fixed error after one attempt.

| Check | Result |
| --- | --- |
| `pixi run pytest -q tests/unit/srv_ctrl/test_gateway_web_entry_command.py tests/unit/agents/realm_controller/test_gateway_client.py` | 24 passed |
| `pixi run pytest -q tests/unit/srv_ctrl` | 660 passed, 13 skipped |
| `pixi run pytest -q tests/integration/agents/realm_controller/test_gateway_https_access.py` | 4 passed on each of two runs after fixture synchronization |
| `pixi run docs-build` | Strict documentation build passed |

The HTTPS fixture used its own tmux socket, temporary CA, verified TLS reverse proxy, and enrolled SSH test signers. The advertised HTTPS endpoint returned HTTP 403 for the bare page, ticket redemption, and an issuance request with valid signed admin proof. Each response carried `Cache-Control: no-store`, `Referrer-Policy: no-referrer`, and no `Location`. Signed admin status remained available before and after the Web route refusals. The test also verified signed self mail status and both public input routes in separate cases.

Before synchronizing the fixture, an attached self status check sometimes captured the gateway's startup line before the CLI JSON. The fixture now waits for production startup to finish. A full HTTPS run also reproduced the existing public input race, with HTTP 409 `dispatch_outcome=not_sent` for the second test input. The fake provider now completes after the HTTP handoff acknowledgment, and the test waits for that worker to settle its owner claim before the next independent input. The same production public dispatch path and handoff assertions run in the fixture. [Prior HTTPS race evidence](../../archive/2026-11-19-honor-explicit-tool-params/logs/gateway-https.md)
