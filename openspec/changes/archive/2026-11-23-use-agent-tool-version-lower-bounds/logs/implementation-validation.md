# Version Minimum Verification

## Live Manager Fixtures

The maintained agent fixture used an explicitly selected executable, the `self-hosted` case, and `Qwen/Qwen3.8-27B-FP8` at the local model endpoint. Each run used an independent private runtime outside the checkout and its own tmux socket. The fixture used a simple response prompt and stopped the agent by its captured managed identity.

| Mode | CLI version | Launch | Managed turn | Stop |
| --- | --- | --- | --- | --- |
| Kimi Web | 2.6.0 | Ready | Completed | Stopped |
| Kimi Web | 2.7.2 | Ready | Completed | Stopped |
| Kimi ACP service | 2.7.2 | Ready | Completed | Stopped |
| Codex app-server service | 0.171.0 | Ready | Completed | Stopped |

The first Kimi Web 2.7.2 run passed the executable check and reached native startup. Its session descriptor reported the workspace as top-level `cwd`, so the older descriptor reader rejected the session. The installed API also reports activity as `idle`, `turn`, or `background` and returns the session and permission mode in a nested profile response. The adapted reader verifies these fields and retains the same host, session, workspace, permission, and queue checks. The repeat run completed successfully. The independent 2.6.0 run verified the earlier response shape.

A separate managed Web fixture on Kimi Code 2.7.2 verified the browser handoff in headless Chromium. The browser consumed the authentication fragment, stayed on the bound session path, and successfully read that exact session through the authenticated native API.

## Automated Checks

The focused Pixi unit run passed 482 tests, with one existing Starlette deprecation warning. The run used a private tmux directory with `TMUX` and `TMUX_PANE` cleared.

```bash
pixi run pytest -q \
  tests/unit/agents/test_launch_policy.py \
  tests/unit/agents/test_dsh_launch_surfaces.py \
  tests/unit/agents/test_kimi_web_backend.py \
  tests/unit/agents/realm_controller/test_{loaders_and_launch_plan,runtime_registry,codex_app_server,kimi_acp_service,service_owner,dsh_web_backend,usage_adapters,usage_support,native_refresh_secondary}.py \
  tests/unit/srv_ctrl/commands/test_agents_core.py \
  tests/unit/srv_ctrl/test_managed_agents.py
```

The managed Web integration passed on DSH 0.2.2-rc.5. It verified that browser and API use the same native session, including after exact relaunch. The fixture selected the self-hosted case and its controlled local model.

```bash
HOUMAO_DSH_EXECUTABLE=/home/huangzhe/.bun/bin/dsh pixi run pytest -q \
  tests/integration/agents/dsh/web/test_fixture_web.py -k 'manager and self-hosted'
```

The usage readers classify captured Kimi ACP 2.7.2 and Codex app-server 0.171.0 observations as `unsupported_client_version` with unknown measurement scope. Fresh live runs with the final code completed managed turns on Kimi Web 2.7.2, Kimi ACP 2.7.2, and Codex app-server 0.171.0 and reported token totals as unavailable. Refresh tests confirmed that startup with a newer build leaves native refresh unsupported when resource evidence is unavailable.

Ruff lint and format checks passed for the changed Python files. Mypy passed for the changed source files. Strict OpenSpec validation passed.
