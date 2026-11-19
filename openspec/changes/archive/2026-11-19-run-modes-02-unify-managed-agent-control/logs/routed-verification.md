# Saved Executor Verification

The fixture runs `houmao-mgr` as an unprivileged operator and executes native DSH Web as a different OS account. Each run uses a private registry and an explicitly selected tmux socket. The operator keeps a separate same-named session to detect accidental fallback. The Linux lane permits one exact sudo helper command, and the SSH lane pins the fixture host key and restricts the owner login. Test credentials and work directories live outside the checkout.

The saved route handles the manager prompt and lifecycle. For gateway control, a fixture admin enrolled inside the selected owner account signs HTTP requests. Enrollment makes an unsigned Web state request return HTTP 401. The authenticated prompt receipt correlates to an active native turn, and interrupt targets that observed turn. Gateway detach and reattach preserve the same native identity. After a gateway-only crash, the manager reads that identity directly, then stops and relaunches through the saved owner. The owner rejects a request carrying the retired generation before admission. The other agent's home and the operator's same-named session survive.

The crash case exposed stale persisted gateway health. The manager state now checks a current endpoint descriptor against the saved owner, execution context, and generation before it publishes `healthy`. Direct native Web observation remains available after the gateway listener exits.

## Results

| Check | Result |
| --- | --- |
| Live DSH Web on Qwen through sudo and pinned SSH | 2 passed in 95.48 seconds |
| Restricted sudo with a controlled provider response | 1 passed in 86.44 seconds, SSH deselected |
| Execution and manager routing unit tests | 167 passed in 1.75 seconds |

The unit tests include one indeterminate saved-owner `describe` request. The manager reports that unreachable owner without a retry or a lookup through the caller's local agent or pair server.

## Reproduce

Use the qualified DSH `0.2.2-rc.3` executable and an explicitly selected self-hosted Qwen endpoint. The test supplies the DSH reasoning mapping, the OpenAI Chat compatibility setting for developer messages, and the fixture's private model configuration.

```bash
env -u TMUX -u TMUX_PANE \
  HOUMAO_EXECUTION_INTEGRATION=1 \
  HOUMAO_EXECUTION_ENTRYPOINT="$PWD/.pixi/envs/default/bin/houmao-mgr" \
  HOUMAO_DSH_EXECUTABLE="$PWD/tmp/dsh/npm-runtime/node_modules/.bin/dsh" \
  HOUMAO_TEST_SELF_HOSTED_MODEL=Qwen/Qwen3.8-27B-FP8 \
  HOUMAO_TEST_SELF_HOSTED_OPENAI_BASE_URL=http://127.0.0.1:14888/v1 \
  pixi run pytest -q -rs -n 2 tests/integration/execution/test_native_owner.py
```

```bash
env -u TMUX -u TMUX_PANE pixi run pytest -q \
  tests/unit/execution tests/unit/srv_ctrl/test_execution_routing.py
```
