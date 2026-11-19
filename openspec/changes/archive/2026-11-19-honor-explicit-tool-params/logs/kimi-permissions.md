# Kimi Permission Qualification

The installed Kimi Code `2.6.0` executable ran each managed fixture against `Qwen/Qwen3.8-27B-FP8` through the explicit `self-hosted` case. Each fixture used an owner-only run directory, isolated tmux, and a signed gateway. The explicit tests set `tool_params.permission_mode` with `houmao-mgr project specialist set --tool-params` before launch. All workload prompts requested text only.

| Managed Mode | Omitted Permission Field | Authored Permission Field | Exact Relaunch |
| --- | --- | --- | --- |
| TUI | `auto` in `config.toml`, final `--auto`, and native journal | `yolo` in config, final `--yolo`, and journal | Each fixture completed a second turn in the original native conversation and retained native `SYSTEM.md`. |
| ACP service | ACP selected `auto` and a workload turn completed | `manual` mapped to the verified ACP `default` ID and a workload turn completed | Each fixture retained its native session ID and verified the effective mode in the new owner binding. |
| Web | `auto` in config and native permission journal | `manual` in config and journal | Each fixture retained its native session ID and reapplied the startup setting. A live session change to `yolo` survived gateway reattachment and a manager state query. |

The installed Web build accepts a permission update through `POST /api/v1/sessions/{session_id}/profile` using `agent_config.permission_mode`. The response confirms the session and workspace and omits a permission echo. The native `permission.set_mode` journal records confirmed the selected mode on fresh and resumed startup. Local native source shows why an explicit `manual` override is unavailable when resuming a TUI session. Kimi restores its saved permissions and provides CLI startup flags for `auto` and `yolo`. The headless native `-p` entrypoint uses `auto`, and launch-plan tests reject an explicit incompatible mode before startup.

The fixture commands used the installed executable and OpenAI Chat endpoint.

```bash
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client kimi --mode "$mode" --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --run-root "$PWD/tmp/kimi-permission-qualification" \
  --executable "$kimi_executable"
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py launch \
  --run-dir "$run_dir" --prompt 'Reply exactly KIMIPERM. Do not use tools.'
```

The focused unit and integration run passed 95 cases. The run covered launch policy, launch plans, TUI continuation arguments, observer hook projection, native Web binding, ACP protocol settlement, starter setup, Kimi headless runtime, and Kimi guidance. It emitted the existing Starlette test-client deprecation warning.

```bash
env -u TMUX -u TMUX_PANE TMUX_TMPDIR="$isolated_tmux_dir" pixi run pytest -q \
  --basetemp=/tmp/ho-kimi-perm-final \
  tests/unit/agents/test_launch_policy.py \
  tests/unit/agents/test_kimi_web_backend.py \
  tests/unit/agents/realm_controller/test_loaders_and_launch_plan.py \
  tests/unit/agents/realm_controller/test_kimi_acp_service.py \
  tests/unit/agents/realm_controller/test_tmux_control_input.py \
  tests/unit/agents/realm_controller/test_kimi_hook_observation_launch.py \
  tests/integration/agents/realm_controller/test_kimi_headless_runtime_contract.py \
  tests/unit/project/test_starter_kimi_adapter.py \
  tests/unit/docs/test_system_skills_kimi_guidance.py \
  tests/unit/agents/realm_controller/test_hook_observation_launch_plan.py \
  -k 'kimi or test_permission'
```
