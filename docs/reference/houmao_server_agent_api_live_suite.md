# Houmao Server Agent API Live Suite

`tests/manual/manual_houmao_server_agent_api_live_suite.py` is the canonical operator-run live suite for direct `houmao-server` managed-agent API verification.

It starts one suite-owned `houmao-server`, provisions the selected managed-agent lanes without a gateway, exercises the public `/houmao/agents/*` routes directly, and preserves launch, request, stop, and shutdown evidence under one run root.

## Supported Lanes

- `claude-tui`
- `codex-tui`
- `claude-headless`
- `codex-headless`

When `--lane` is omitted, the suite runs all four lanes in one aggregate pass.

## Invocation

Run every lane with the default repo-local artifact root:

```bash
pixi run python tests/manual/manual_houmao_server_agent_api_live_suite.py
```

Run only one subset of lanes:

```bash
pixi run python tests/manual/manual_houmao_server_agent_api_live_suite.py \
  --lane claude-tui \
  --lane codex-headless
```

Override the run root:

```bash
pixi run python tests/manual/manual_houmao_server_agent_api_live_suite.py \
  --output-root /tmp/houmao-server-api-live-suite-run
```

Raise the TUI provisioning budget when real provider startup is slow:

```bash
pixi run python tests/manual/manual_houmao_server_agent_api_live_suite.py \
  --compat-create-timeout-seconds 120 \
  --compat-provider-ready-timeout-seconds 120
```

## Prerequisites

The suite fails before server startup if any selected prerequisite is missing.

Required executables:

- `tmux`
- `claude` when any Claude lane is selected
- `codex` when any Codex lane is selected

Tracked fixture assets:

- compatibility profile: `tests/fixtures/agents/compatibility-profiles/server-api-smoke.md`
- role: `tests/fixtures/agents/roles/server-api-smoke/`
- recipes and blueprints under `tests/fixtures/agents/brains/brain-recipes/*/server-api-smoke-default.yaml` and `tests/fixtures/agents/blueprints/server-api-smoke-*.yaml`
- copied dummy-project source: `tests/fixtures/dummy-projects/mailbox-demo-python/`

Credential expectations:

- Claude lanes read the tracked local credential profile at `tests/fixtures/agents/brains/api-creds/claude/personal-a-default/env/vars.env` and require `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`.
- Codex lanes run in API-key mode for this suite version and use the tracked `yunwu-openai` fixture pair:
  `tests/fixtures/agents/brains/cli-configs/codex/yunwu-openai/config.toml`
  `tests/fixtures/agents/brains/api-creds/codex/yunwu-openai/env/vars.env`
  The env file must set `OPENAI_API_KEY`. `OPENAI_BASE_URL` and `OPENAI_ORG_ID` remain optional pass-through values when your local profile needs them.
- The suite injects the selected env vars into the suite-owned `houmao-server` process for TUI lanes and reuses the same tracked credential profiles for headless launch materialization.

## Timeouts

The suite makes use of the configurable compatibility timeouts now exposed in the repository:

- `--compat-http-timeout-seconds`: suite client timeout for normal HTTP calls
- `--compat-create-timeout-seconds`: client-side budget for `POST /cao/sessions`
- `--compat-provider-ready-timeout-seconds`: server-side compatibility provider-ready budget passed to `houmao-server serve`
- `--health-timeout-seconds`: owned-server readiness budget
- `--prompt-timeout-seconds`: bounded polling budget for post-request state change and headless turn completion

The initial TUI create/provider-ready default is 90 seconds.

## Artifact Layout

Without `--output-root`, runs are staged under:

```text
tmp/tests/houmao-server-agent-api-live-suite/<timestamp>/
```

Important artifacts:

- `config.json`: resolved invocation and timeout settings
- `preflight.json`: prerequisite and fixture checks
- `summary.json`: final suite status plus per-lane summaries
- `server/start.json`: selected API base URL, owned roots, and current-instance snapshot
- `server/shutdown.json`: owned-server shutdown evidence
- `http/*.json`: suite-level HTTP snapshots such as health and `GET /houmao/agents`
- `lanes/<lane-id>/launch.json`: launch metadata and managed identity details
- `lanes/<lane-id>/route-verification.json`: `GET /houmao/agents/*` verification snapshots
- `lanes/<lane-id>/prompt-verification.json`: `POST /requests` admission plus post-request state evidence
- `lanes/<lane-id>/stop.json`: stop-route and best-effort cleanup results
- `lanes/<lane-id>/http/*.json`: per-lane request/response snapshots
- `lanes/<lane-id>/headless-turns/<turn-id>/`: durable turn status, events, `stdout.txt`, and `stderr.txt` for headless lanes that return a turn handle

The suite preserves the run root after both success and failure so operators can inspect the evidence without rerunning the live flow.
