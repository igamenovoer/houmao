# Gateway Web Entry Verification

The gateway tests exercised real retained enrollment and request-bound SSHSIG. They verified direct admin admission, rejection of self and delegated proof, fixed responses for hostile URLs and provider errors, and exact owner-local ingress. Deterministic clocks and concurrent requests verified one-time approval, claim, and redemption, including expiry during native revalidation and revocation after issuance. A listener restart or a replacement execution with the same native session ID refused the old grant.

| Check | Result |
| --- | --- |
| `pixi run lint` | Passed |
| `pixi run typecheck` | Passed, 525 source files |
| `pixi run test --basetemp=/tmp/hweb-full-checked` | 5,063 passed, 14 skipped |
| `pixi run docs-build` | Strict build passed |
| `openspec validate add-gateway-web-entry --strict` | Passed |
| `tests/unit/agents/realm_controller/test_gateway_web_entry.py` | 15 passed |
| `tests/integration/agents/realm_controller/test_gateway_runtime_contract.py` | 12 passed |
| `tests/integration/agents/realm_controller/test_gateway_https_access.py` | 4 passed on two isolated runs |
| DSH Web `test_browser_coexistence.py` and `test_native_control.py` | 32 passed with DSH 0.2.2-rc.3 |
| DSH Web fixture, native gateway, projection, and managed lifecycle suites | 18 passed with DSH 0.2.2-rc.3 |

Unit and integration runs unset inherited tmux coordinates and used isolated scratch roots. The DSH regression selected the qualified executable explicitly with `HOUMAO_DSH_EXECUTABLE`. Live DSH 0.2.2-rc.3 and Kimi Code 2.6.0 both used the explicitly selected self-hosted `Qwen/Qwen3.8-27B-FP8` model and fresh Chromium profiles.

The Kimi run used private OpenSSH TCP forwarding through a SOCKS5 listener that retained both owner addresses. The environment denied creation of a second network namespace for the static `ssh -L` example. The HTTPS suite reproduced an earlier public-prompt timing race before synchronizing the test fixture's acknowledgment and completion steps. The full module passed on two subsequent runs.

[DSH browser qualification](dsh.md), [Kimi browser qualification](kimi.md), [Manager and HTTPS verification](cli-and-https.md)
