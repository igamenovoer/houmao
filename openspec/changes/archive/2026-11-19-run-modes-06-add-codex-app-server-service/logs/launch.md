# Launch and Manifest Verification

`houmao-mgr project agents launch --mode service` resolves Codex to `codex_app_server`. Startup resolves the selected executable to an absolute path and requires Codex CLI `0.169.0`. The supervisor launches `app-server --listen stdio://` in the selected workspace with the private `CODEX_HOME`. The plan rejects raw launcher arguments, checks the credential projection, and supplies the configured model and Responses provider as typed thread configuration. Role instructions use the native `developerInstructions` field. The unattended launch strategy prepares workspace trust and applies the native approval and sandbox policy when the owner binds the thread.

The manifest stores a service incarnation and native thread alongside the runtime generation and exact tmux selectors. Its tmux pane serves as supervisor logs and the service has no human terminal surface. Current manifest validation checks the saved service state against the runtime, workspace and pane authority. An old schema or retired Codex PID record directs the operator to a fresh launch. Attaching a controller to the current service uses the saved launch posture. An explicit relaunch rebuilds the provider startup plan.

## Checks

```bash
env -u TMUX -u TMUX_PANE pixi run pytest -q \
  tests/unit/agents/realm_controller/{test_run_modes,test_loaders_and_launch_plan,test_schema_consistency,test_service_owner,test_schema_and_manifest}.py \
  tests/unit/agents/test_launch_policy.py tests/unit/execution/test_locators.py
```

All 162 focused tests passed. They cover service mode selection, unchanged Codex headless and TUI defaults, accepted and refused builds, alternate listeners and daemon arguments, selected private configuration, schema alignment, and retirement of old or mismatched owner authority. Ruff and strict mypy passed for the changed launch and runtime modules. The live Qwen checks are recorded separately in this change's implementation log.
