# Selection and Host Verification

This log records the initial qualification gate, before the user selected the TUI readiness policy. See [current selection and verification](check-and-send.md).

The project CLI, direct runtime, and fixture helper report the missing atomic ready-only prompt operation and list the supported Kimi modes, `headless`, `service`, and `tui`. Direct runtime selection runs after it reads the tool identity and before it resolves the runtime root, prepares the role, or starts a provider. Project CLI selection precedes launch catalog projection and force takeover. The raw and manager fixture commands both return a refusal without creating the requested run directory. The mode resolver does not add a Kimi Web backend or browser surface.

```bash
env -u TMUX -u TMUX_PANE pixi run pytest -q \
  tests/unit/agents/realm_controller/test_run_modes.py \
  tests/unit/agents/realm_controller/test_runtime_registry.py::test_kimi_web_rejects_before_runtime_or_native_start \
  tests/unit/srv_ctrl/test_project_commands.py::test_project_rejects_kimi_web_before_workspace_or_force_takeover \
  tests/integration/agents/test_agent_fixture_launches.py::test_fixture_refuses_kimi_web_before_preparing_run
```

All 24 tests passed. A broader run of `test_run_modes.py`, `test_runtime_registry.py`, `test_project_commands.py`, and the fixture refusal cases passed 168 tests and skipped 13. Ruff and strict mypy passed for the changed Python modules.

A separate metadata probe started the installed Kimi Code `2.6.0` with `kimi web --host 127.0.0.1 --port 0 --no-open`, an empty private home, and no model credentials. The native instance record identified the child PID and actual loopback port. Linux process descriptors confirmed that the child held the listening socket before the probe sent a bearer. The health endpoint returned HTTP 200. Unsigned metadata returned HTTP 401, and authenticated metadata and OpenAPI requests returned HTTP 200. The prompt submission schema contained no conditional admission field or header. The native process printed the bearer to its private startup capture despite `--no-open`.

The `server_id` in the authenticated metadata differed from the ID in the native instance record. The local source generates these IDs independently, so future host verification needs to bind each observation to the launched process and listener. The probe stopped the captured process and removed the temporary home and private output. It sent no model prompt. [Native metadata registration](../../../../extern/orphan/kimi-code/packages/kap-server/src/routes/registerApiV1Routes.ts), [instance registry](../../../../extern/orphan/kimi-code/packages/kap-server/src/instanceRegistry.ts).
