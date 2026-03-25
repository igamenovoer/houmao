# CLI And Environments

`Houmao` uses a standalone Pixi manifest in this repository.

## Install

```bash
pixi install
```

## Primary Commands

- Runtime CLI: `houmao-cli`
- Retired standalone launcher: `houmao-cao-server`
- Houmao server CLI: `houmao-server`
- Houmao management CLI: `houmao-mgr`

Runtime subcommands:

- `build-brain`
- `start-session`
- `send-prompt`
- `send-keys`
- `mail`
- `stop-session`

Module equivalents:

```bash
pixi run python -m houmao.agents.realm_controller --help
pixi run python -m houmao.cao.tools.cao_server_launcher   # retired: exits with migration guidance
houmao-server --help
houmao-mgr --help
```

## Common Runtime Flags

Useful `start-session` overrides:

- `--cao-base-url http://localhost:<port>` or `http://127.0.0.1:<port>` for a supported launcher-managed loopback CAO endpoint
- `--houmao-base-url http://127.0.0.1:<port>` for the `houmao_server_rest` runtime backend
- `--mailbox-transport filesystem`
- `--mailbox-root <path>`
- `--mailbox-principal-id <principal-id>`
- `--mailbox-address <full-address>`

Useful `build-brain` or `houmao-mgr brains build` override:

- `--operator-prompt-mode unattended` to request versioned unattended launch-policy resolution for the built brain instead of the default interactive posture

The paired replacement for `cao-server + cao` is `houmao-server + houmao-mgr`. Mixed use with raw `cao-server` or raw `cao` is intentionally unsupported for this path. Use [Houmao Server Pair](houmao_server_pair.md) for the contract boundary.

For pair-managed agents, the preferred operator surface is still the managed-agent command family on `houmao-mgr` and the matching `/houmao/agents/*` server routes. When an attached gateway is healthy, those same commands automatically gain richer live backing behavior such as gateway-owned admission, queueing, and live state projection without changing the public CLI shape.

Within that pair, `houmao-mgr` is split deliberately:

- `server` is the server lifecycle and server-session family
- `agents` is the managed-agent lifecycle family
- `brains` is the local brain-construction family
- `admin` is the local maintenance family

The explicit `houmao-mgr cao ...` namespace and top-level `houmao-mgr launch` are retired from the supported command tree.

Useful pair runtime controls:

- `houmao-mgr agents launch --agents <selector> --provider <provider>` performs local brain build plus launch without requiring a running `houmao-server`.
- `houmao-mgr server start` is detached by default, emits one structured startup result, and accepts `--foreground` when you want the server attached to the current terminal.
- `houmao-mgr server start` exposes the same server startup flags as `houmao-server serve`, including `--compat-shell-ready-timeout-seconds`, `--compat-shell-ready-poll-interval-seconds`, `--compat-provider-ready-timeout-seconds`, `--compat-provider-ready-poll-interval-seconds`, and `--compat-codex-warmup-seconds`.
- `houmao-mgr server stop`, `houmao-mgr server status`, and `houmao-mgr server sessions ...` are the supported server-management commands.

Detached startup results include `success`, `running`, `mode`, `api_base_url`, `detail`, and server identity fields when available. On failed detached startup, inspect the owned log files under `<runtime-root>/houmao_servers/<host>-<port>/logs/`.

For pair-managed terminal sessions, the public gateway attach surface also lives on the pair CLI:

- `houmao-mgr agents gateway attach <agent-ref> --port <public-port>` for explicit managed-agent targeting
- `houmao-mgr agents gateway attach` from inside the target tmux session for current-session attach

Current-session attach requires the target tmux session to publish `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`, and it becomes valid only after the matching managed-agent registration exists on the persisted `api_base_url`.

For ordinary pair-native prompt submission, prefer `houmao-mgr agents prompt <agent-ref> --prompt "..."`. That command stays on the preferred managed-agent seam and lets the server choose direct fallback or live gateway control safely. Use `houmao-mgr agents gateway prompt <agent-ref> --prompt "..."` only when you explicitly want to require live-gateway admission and queue semantics.

For pair-owned mailbox follow-up, use `houmao-mgr agents mail status|check|send|reply ...`. For local artifact or maintenance work that should not hit `houmao-server`, use `houmao-mgr brains build ...` and `houmao-mgr admin cleanup-registry ...`.

The runtime `mail` command operates on resumed mailbox-enabled sessions and supports `check`, `send`, and `reply`.

When `start-session` is used with `--json`, unattended sessions may also return:

- `launch_policy_provenance` with the requested mode, detected CLI version, selected strategy id, and whether resolution came from the registry or the transient override env var
- `launch_policy` with the resolved strategy metadata that was attached to the launch plan

Command reminders:

- `mail send` recipients must use full mailbox addresses such as `AGENTSYS-orchestrator@agents.localhost`.
- `mail send` and `mail reply` require body content via `--body-file` or `--body-content`.
- `send-keys` is the low-level CAO control-input surface for resumed legacy `cao_rest` sessions; new standalone `backend="cao_rest"` operator workflows are retired in favor of `houmao-server` with `houmao-mgr`.
- Managed-agent routes and `agents ...` commands are the preferred pair seam. The retired CAO compatibility namespace is no longer part of the supported operator workflow.

For the dedicated mailbox quickstart, contracts, and operational guidance, see [Mailbox Reference](mailbox/index.md).

## Agent Definition Directory

Runtime commands use two agent-definition-directory resolution models:

1. Build/start and manifest-path control: `--agent-def-dir`, then `AGENTSYS_AGENT_DEF_DIR`, then `<pwd>/.agentsys/agents`.
2. Name-based tmux-backed `send-prompt`, `send-keys`, `mail`, and `stop-session`: explicit `--agent-def-dir` override first, otherwise the addressed session's published `AGENTSYS_AGENT_DEF_DIR`.

## Pixi Tasks

```bash
pixi run format
pixi run lint
pixi run typecheck
pixi run test-runtime
pixi run build-dist
pixi run check-dist
```
