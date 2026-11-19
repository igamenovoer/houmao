# DSH Permission and Self-Status Qualification

## Live Fixture

Ran the checkout manager and DSH `0.2.2-rc.3` against self-hosted `Qwen/Qwen3.8-27B-FP8`. Each invocation used a private fixture directory under the ignored `tmp/honor-explicit-dsh-qualification/` tree and an isolated tmux socket. The sibling write target was outside the fixture workdir and the operating system's temporary directories.

```bash
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client dsh --mode "$mode" --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"off":"none","low":"low","medium":"medium","high":"high"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable "$PWD/tmp/dsh/npm-runtime/node_modules/.bin/dsh" \
  --run-root "$run_root"
```

The default fixtures left both permission fields unset. The restricted fixture added `permissions.sandbox: workspace-write` and `permissions.approval: never` to its selected `tool-params.yaml`. After `fixture.py launch`, the prompt asked Bash to write a fixed marker in the sibling directory without escalation. The check read the actual file and the native tool result.

| Backend and Effective Permissions | Fixture ID Suffix | Outcome |
| --- | --- | --- |
| Headless, `danger-full-access` + `never` | `9f9fc1e9e745` | Turn `turn-0bb3324cfb66` completed and created the marker. |
| Headless, `workspace-write` + `never` | `881a51bdc41e` | Turn `turn-ada2317de80b` completed. Bash reported permission denied and the marker was absent. |
| ACP service, `danger-full-access` + `never` | `ea4a672c08f1` | Turn `turn-bf258f7ee989` completed and created the marker. The native binding confirmed the selected preset. |
| Web, `danger-full-access` + `never` | `cd8ae84f712d` | Turn `turn-1e20a688ebee` completed and created the marker. |

The restricted fixture ran `houmao-mgr agents self state` and `houmao-mgr agents self mail status` in its Bash tool during turn `turn-d41d49819ee2`. Both commands exited zero. The state reported `availability: available`, and the mail status returned the current channel status. The registry was outside the sandbox write boundary. Each final fixture reported `stopped_owned_identity` after `fixture.py stop`.

## Controlled Checks

| Check | Result |
| --- | --- |
| `test_dsh_configuration.py`, `test_dsh_fixture_tools.py`, `test_dsh_launch_surfaces.py`, and `test_dsh_headless_worker.py` | 152 passed. The five added starter and repeated-start cases passed on a separate invocation. |
| Final `test_dsh_configuration.py` and `test_dsh_launch_surfaces.py` after atomic profile replacement | 126 passed. |
| `test_dsh_launch_surfaces.py`, `test_dsh_acp_service.py`, and `test_dsh_web_backend.py` | 72 passed before the five additional starter and repeated-start cases. |
| Native `test_fixture_headless.py` and `test_headless_dispatch_permission.py` | 6 passed with the selected DSH binary. They include exact resume and preservation of the JSON output and dispatch fence. |
| Native `test_fixture_service.py` and `test_service_gateway.py` | 3 passed with the selected DSH binary. They include a persistent service and exact continuation. |
| Native `test_browser_coexistence.py` and `test_native_control.py` | 32 passed with the selected DSH binary and headless Chromium. An unattended Web launch with explicit `workspace-write` and `ask` displayed a native escalation request and reported an interaction wait through the API. |
| Ruff and strict mypy on the changed DSH Python implementation | Passed. |

An early headless probe showed that patching the native runner's configuration replaced its JSON mode and session option wiring. The final implementation reads the materialized profile and passes its preset through native `--permission-mode`. The first ACP probe exposed that a startup policy confirmation was being treated as part of the per-turn receipt identity. The final implementation verifies the policy at startup and keeps the receipt identity unchanged.
