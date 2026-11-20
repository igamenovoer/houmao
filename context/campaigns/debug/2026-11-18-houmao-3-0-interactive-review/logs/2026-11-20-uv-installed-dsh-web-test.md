# UV-Installed Houmao DSH Web Test

Date: 2026-11-20. Status: DSH Web launched and verified through the uv-installed Houmao package. The first uv environment failed at gateway startup because it used Python 3.12. Reinstalling the tool on Python 3.13 resolved it.

Plan: [Iteration 2](../iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md). Related mapping/auth log: [DSH Web authentication and Qwen xhigh mapping](2026-11-19-dsh-web-auth-and-xhigh-mapping.md).

## Installed Package Refresh

The existing uv tool was a stale `3.0.0rc3` build from before commit `18b864d2`: it still defaulted DSH to `workspace-write`, lacked the read-only self-control path, and had no `gateway web-entry` command.

The tool was reinstalled from the checkout with:

```bash
uv tool install --force --reinstall /data/huangzhe/code/houmao
```

That installation selected the system Python 3.12. Web launch then failed before gateway health because Pydantic passed a `ValidationInfo` object into `validate_gateway_base_url()`:

```text
TypeError: object of type ValidationInfo has no len()
```

The traceback ended at:

```text
houmao/gateway/deployment.py:55 in _validate_advertised_url
houmao/gateway/access_models.py:329 in validate_gateway_base_url
```

Pinning Pydantic to `2.13.4` did not fix the failure under Python 3.12. The tool was then reinstalled on Python 3.13 with:

```bash
uv tool install --python 3.13 --force --reinstall \
  --with 'pydantic==2.13.4' /data/huangzhe/code/houmao
```

The uv tool then reported Python `3.13.18` and Pydantic `2.13.4`, matching the working Pixi runtime. No product source or test file was changed by this workaround.

## Verified Web Run

The fixture itself was executed with the uv tool interpreter, so `fixture.py` and its in-process manager calls imported the uv-installed `houmao` package:

```bash
/home/huangzhe/.local/share/uv/tools/houmao/bin/python \
  scripts/agents/test-fixtures/fixture.py ...
```

Run details:

- Run: `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9`
- Agent: `49f2ba49-e7be-4463-bdbf-a788f4ff9596`
- Runtime session: `dsh_web-20261120-030332Z-03394014`
- Native session: `session-c22df0f3-5c06-4362-bab0-897fc205c0c0`
- Browser origin: `http://127.0.0.1:46039`
- Gateway: `http://127.0.0.1:36205`
- Tmux session: `HOUMAO-self-hosted-dsh-web-manager-2752bd4a0bc9-1795143812150`

`houmao-mgr agents single ... state` through the uv CLI returned `availability: available`, `gateway_health: healthy`, and `connection_ready: true`. The fixture live check returned `status: launched`, no missing prerequisites, and healthy usage collection.

The DSH tool parameters used the corrected mapping:

```json
{"off":"none","low":"low","medium":"medium","xhigh":"xhigh"}
```

The project specialist was set to reasoning level 3, and the native profile materialized `reasoning: xhigh`.

The DSH workspace was registered through `/api/workspace/create`, then a native prompt `Reply with exactly UV-WEB-XHIGH-OK.` was admitted and completed. The native request header recorded:

```json
{"provider":"houmao-self-hosted","model":"Qwen/Qwen3.8-27B-FP8","reasoningEffort":"xhigh"}
```

The maintained Playwright driver signed in from the fixture descriptor, selected `session-c22df0f3-5c06-4362-bab0-897fc205c0c0`, and found `UV-WEB-XHIGH-OK`.

A private sign-in URL is at `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9/sign-in-url.txt` with mode `0600`; the token is not recorded here.

The operator watch script is `tmp/houmao-30-iter2-rc3/attach-web.sh`. It resolves the tmux session and socket from the session manifest at execution time (`--print-target` prints them) instead of embedding the session name; the convention is recorded in [debug-intent.md](../debug-intent.md#operator-watch-scripts).

## Findings

- The uv-installed package works on Python 3.13 with Pydantic 2.13.4.
- The same package fails during gateway startup under Python 3.12, even with Pydantic 2.13.4. The declared Python floor therefore does not reflect the tested Web-gateway runtime.
- The installed package still has no `gateway web-entry` implementation; that remains the OpenSpec proposal `openspec/changes/add-gateway-web-entry/` and GitHub issue #88.
- No production code was modified for this test; only the uv tool environment and campaign records were changed.
