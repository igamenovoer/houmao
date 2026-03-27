# Houmao Server Agent API Live Suite

> **Legacy / Deprecated:** This document describes a demo-pack-based live validation workflow that predates the current `houmao-server` + `houmao-mgr` pair architecture. The test harness and demo-pack artifacts referenced below may no longer reflect the current API surface. For the current managed-agent API reference, see [Managed-Agent API](managed_agent_api.md). For the current server pair architecture, see [Houmao Server Pair](houmao_server_pair.md).

## Overview

This suite validates the `/houmao/agents/*` managed-agent API routes by starting a dedicated `houmao-server`, provisioning managed-agent lanes without a gateway, exercising the public routes directly, and preserving launch/request/stop/shutdown evidence under one run root.

## Supported Lanes

- `claude-tui`
- `codex-tui`
- `claude-headless`
- `codex-headless`

When `--lane` is omitted, the suite runs all four lanes in one aggregate pass.

## Invocation

Run every lane with the default repo-local artifact root:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh auto
```

Run only one subset of lanes:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh start \
  --lane claude-tui \
  --lane codex-headless
```

Override the run root:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh auto \
  --demo-output-dir /tmp/houmao-server-api-live-suite-run
```

Raise the TUI provisioning budget when real provider startup is slow:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/run_demo.sh auto \
  --compat-create-timeout-seconds 120 \
  --compat-provider-ready-timeout-seconds 120
```

Run the named HTT/autotest harness:

```bash
scripts/demo/houmao-server-agent-api-demo-pack/autotest/run_autotest.sh \
  --case real-agent-all-lanes-auto
```

## Prerequisites

The suite fails before server startup if any selected prerequisite is missing.

Required executables:

- `tmux`
- `claude` when any Claude lane is selected
- `codex` when any Codex lane is selected

Tracked fixture assets:

- role: `scripts/demo/houmao-server-agent-api-demo-pack/agents/roles/server-api-smoke/`
- recipes and blueprints under `scripts/demo/houmao-server-agent-api-demo-pack/agents/brains/brain-recipes/*/server-api-smoke-default.yaml` and `scripts/demo/houmao-server-agent-api-demo-pack/agents/blueprints/server-api-smoke-*.yaml`
- copied dummy-project source: `scripts/demo/houmao-server-agent-api-demo-pack/inputs/project-template/`

Credential expectations:

- Claude lanes read the local-only pack profile at `scripts/demo/houmao-server-agent-api-demo-pack/agents/brains/api-creds/claude/personal-a-default/env/vars.env` and require `ANTHROPIC_API_KEY` or `ANTHROPIC_AUTH_TOKEN`.
- Codex lanes run in API-key mode for this suite version and use the tracked `yunwu-openai` fixture pair:
  `scripts/demo/houmao-server-agent-api-demo-pack/agents/brains/cli-configs/codex/yunwu-openai/config.toml`
  `scripts/demo/houmao-server-agent-api-demo-pack/agents/brains/api-creds/codex/yunwu-openai/env/vars.env`
  The env file must set `OPENAI_API_KEY`. `OPENAI_BASE_URL` and `OPENAI_ORG_ID` remain optional pass-through values when your local profile needs them.
- The suite injects the selected env vars into the suite-owned `houmao-server` process for TUI lanes and reuses the same local pack credential profiles for headless launch materialization.

## Timeouts

The suite makes use of the configurable compatibility timeouts now exposed in the repository:

- `--compat-http-timeout-seconds`: suite client timeout for normal HTTP calls
- `--compat-create-timeout-seconds`: client-side budget for session creation
- `--compat-provider-ready-timeout-seconds`: server-side compatibility provider-ready budget passed to `houmao-server serve`
- `--health-timeout-seconds`: owned-server readiness budget
- `--prompt-timeout-seconds`: bounded polling budget for post-request state change and headless turn completion

The initial TUI create/provider-ready default is 90 seconds.

## Artifact Layout

Without `--demo-output-dir`, runs are staged under:

```text
scripts/demo/houmao-server-agent-api-demo-pack/outputs/runs/<timestamp>/
```

Important artifacts:

- `control/config.json`: resolved invocation and timeout settings
- `control/preflight.json`: prerequisite and fixture checks
- `control/shared_routes.json`: `GET /houmao/agents` verification snapshot
- `control/report.json`: raw verification report
- `control/report.sanitized.json`: sanitized verification report
- `control/verify_result.json`: expected-report comparison result
- `control/stop_result.json`: per-lane stop plus owned-server shutdown evidence
- `server/start.json`: selected API base URL, owned roots, and current-instance snapshot
- `server/shutdown.json`: owned-server shutdown evidence
- `http/*.json`: suite-level HTTP snapshots such as health and `GET /houmao/agents`
- `lanes/<lane-id>/launch.json`: launch metadata and managed identity details
- `lanes/<lane-id>/route-verification.json`: `GET /houmao/agents/*` verification snapshots
- `lanes/<lane-id>/prompt-verification.json`: `POST /requests` admission plus post-request state evidence
- `lanes/<lane-id>/interrupt-verification.json`: interrupt request and follow-up evidence when `interrupt` is used
- `lanes/<lane-id>/stop.json`: stop-route and best-effort cleanup results
- `lanes/<lane-id>/http/*.json`: per-lane request/response snapshots
- `lanes/<lane-id>/headless-turns/<turn-id>/`: durable turn status, events, `stdout.txt`, and `stderr.txt` for headless lanes that return a turn handle
- `logs/autotest/<case-id>/`: per-phase HTT case stdout/stderr logs

The suite preserves the run root after both success and failure so operators can inspect the evidence without rerunning the live flow.
