# DSH Web Authentication and Qwen Xhigh Mapping

Date: 2026-11-19. Status: DSH Web relaunched with the corrected Qwen reasoning mapping. Browser, native session, gateway, and `reasoningEffort: xhigh` were verified.

Plan: [Iteration 2](../iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md). Related H1 run: [H1 results](2026-11-19-h1-rc3-headless-execution.md).

## DSH Web Authentication

DSH Web authentication is native to DSH, not added by Houmao. DSH's `dsh-client-connection` documentation states that every Web RPC and stream requires an authenticated browser or API peer, with no loopback-only exemption. Each DSH process creates a random launch token. DSH prints a `?token=` sign-in URL, exchanges the token for a signed, authority-bound cookie, and redirects to the clean origin. A request without a valid cookie returns:

```text
dsh web authentication required; reopen the URL printed by dsh web.
```

Houmao captures DSH's native token from the bootstrap output. The fixture exposes it only through `browser-connection.json`; the raw origin alone returns `401`. The maintained Playwright driver read the descriptor and signed in successfully.

## Qwen Reasoning Effort Probe

The endpoint reports SGLang serving `Qwen/Qwen3.8-27B-FP8`. Direct minimal requests produced:

| `reasoning_effort` | Result |
| --- | --- |
| `low` | HTTP 200, reasoning content present |
| `medium` | HTTP 200, reasoning content present |
| `xhigh` | supported; SGLang calls it the default |
| `high` | HTTP 400 |
| `none` | HTTP 200, no reasoning content |

The `high` error was:

```text
Unexpected reasoning effort high. Supported types are xhigh (default), medium, and low.
```

The previous launch configuration mapped DSH slot `high` to wire value `high`. That mapping was valid to Houmao's structural DSH validation but invalid to this provider. The mapping was corrected to:

```json
{"off":"none","low":"low","medium":"medium","xhigh":"xhigh"}
```

The reusable fixture README and Iteration 2 command now use `xhigh`. The older preparation evidence retains the command actually used and carries a correction note.

## Relaunched Web Agent

After stopping the previous Web run, a new run was prepared with the corrected mapping:

- Run: `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-83fb842c858d`
- Agent: `0bedcbd5-877d-41b7-abd5-18710724bee4`
- Runtime session: `dsh_web-20261119-154504Z-e44d81f2`
- Native session: `session-1aa161e2-4506-406a-9d49-24b4ad41656d`
- Browser origin: `http://127.0.0.1:42769`
- Gateway: `http://127.0.0.1:38595`
- Tmux session: `HOUMAO-self-hosted-dsh-web-manager-83fb842c858d-1795103104180`

The project specialist was set to reasoning level 3 after preparation, so the native profile materialized:

```json
"reasoningEfforts": {
  "low": "low",
  "medium": "medium",
  "off": "none",
  "xhigh": "xhigh"
},
"reasoning": "xhigh"
```

The DSH workspace was registered through `/api/workspace/create`. A native API prompt `Reply with exactly XHIGH-OK.` was admitted and completed. The native journal request header records:

```json
{"provider":"houmao-self-hosted","model":"Qwen/Qwen3.8-27B-FP8","reasoningEffort":"xhigh"}
```

The maintained Playwright browser driver signed in, selected `session-1aa161e2-4506-406a-9d49-24b4ad41656d`, and found `XHIGH-OK`.

A private sign-in URL is stored mode `0600` at `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-83fb842c858d/sign-in-url.txt`; the token is not recorded here.

## Outcome

- DSH Web authentication requirement: confirmed native DSH behavior.
- `high` reasoning wire value: unsupported by this SGLang endpoint.
- Corrected mapping: `high`-equivalent behavior is now the explicit `xhigh` slot.
- Live Web verification: browser sign-in, workspace registration, native session selection, completed prompt, and `XHIGH-OK` all passed.
- No product source or test code was changed for this correction; only fixture documentation, campaign planning/evidence text, and generated run state changed.
