# Implementation Validation

## Native Lifecycle

The managed Workspace lifecycle regression passed on DSH `0.2.2-rc.1`, `0.2.2-rc.3`, and `0.2.2-rc.5`. Each run selected the local controlled Messages model `controlled` and used an isolated tmux server. The native Workspace and session feeds showed one managed session before the first prompt. Two exact relaunches preserved the Workspace and session IDs. New-session relaunch and in-place reset each added one member in that Workspace and preserved both earlier history and an unrelated Workspace.

The companion tests verified rejected workdir registration, rejected attachment followed by retry of the exact session, and attachment that committed before reporting an error. The tests checked managed readiness and diagnostic redaction. [Lifecycle regression](../../../../tests/integration/agents/dsh/web/test_managed_lifecycle.py) · [Companion regression](../../../../tests/unit/agents/realm_controller/test_dsh_web_companion.py)

## Gateway Credential Flows

A manager fixture selected the `self-hosted` case, model `controlled`, and a synthetic local OpenAI-compatible endpoint. On DSH `0.2.2-rc.1` and `0.2.2-rc.5`, Playwright Chromium `159.0.8154.6` opened the same fresh managed session in separate clean contexts through three entry paths. The paths were bare entry with an empty roster, an admin-signed one-time ticket, and interactive login with a temporary Ed25519 key and the page's generated signing command. Each final URL was clean. The browser issued zero startup create requests, and the model received zero requests during entry.

The smoke used `pixi run python -m pytest -q -s -p tests.integration.agents.dsh.conftest tmp/issue92-gateway-entry/test_gateway_entry.py` for each explicitly selected `HOUMAO_DSH_EXECUTABLE`. Fixture state, test credentials, and browser descriptors stayed in owner-private test directories. [Browser Startup Qualification](browser-startup-qualification.md)

## Browser Lifecycle and Notifier

The maintained manager fixture passed on rc.1 and rc.5 with the `self-hosted` case, the local controlled OpenAI Chat model `controlled`, and Chromium `159.0.8154.6`. It observed selection before any prompt, on ordinary reload, and after exact and new-session relaunch. After the browser saved an unrelated selection, the notifier completed a turn in the managed session. Re-entry displayed that turn and preserved both Workspace memberships and the unrelated history. The product browser gate also rejected a reset that occurred between the authenticated page response and its live target check. [Maintained manager test](../../../../tests/integration/agents/dsh/web/test_fixture_web.py) · [Browser Startup Qualification](browser-startup-qualification.md)

## Regression Commands

The focused unit regression passed 232 tests. The rc.3 native Web lifecycle, gateway, and browser coexistence regression passed 20 tests. The rc.3 maintained headless and ACP fixture regression passed 5 tests with controlled endpoints. The rc.5 existing manager browser fixture passed its controlled self-hosted case.

```bash
env -u TMUX -u TMUX_PANE pixi run pytest -q \
  tests/unit/agents/realm_controller/test_dsh_web_*.py \
  tests/unit/agents/realm_controller/test_dsh_acp_*.py \
  tests/unit/agents/realm_controller/test_dsh_headless_worker.py \
  tests/unit/agents/realm_controller/test_gateway_{access_http,web_entry}.py \
  tests/unit/agents/realm_controller/test_native_web_entry.py \
  tests/unit/gateway/test_web_login.py

env -u TMUX -u TMUX_PANE pixi run pytest -q --tb=short \
  tests/integration/agents/dsh/web/test_fixture_web.py -k selects_bound_workspace

env -u TMUX -u TMUX_PANE pixi run pytest -q \
  tests/integration/agents/dsh/web/test_managed_lifecycle.py \
  tests/integration/agents/dsh/web/test_gateway_native.py \
  tests/integration/agents/dsh/web/test_browser_coexistence.py

env -u TMUX -u TMUX_PANE pixi run pytest -q \
  tests/integration/agents/dsh/test_fixture_headless.py \
  tests/integration/agents/dsh/test_fixture_service.py
```

The native commands used an explicit `HOUMAO_DSH_EXECUTABLE`, separate runtime homes, and isolated tmux sockets. Browser tests used clean contexts. Ruff, mypy for the changed Python runtime files, JavaScript syntax checks, and strict OpenSpec validation passed. The built wheel contains all four browser entry assets.
