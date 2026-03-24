# CLI And Environments

`Houmao` uses a standalone Pixi manifest in this repository.

## Install

```bash
pixi install
```

## Primary Commands

- Runtime CLI: `houmao-cli`
- CAO launcher CLI: `houmao-cao-server`
- Houmao server CLI: `houmao-server`
- Houmao pair CLI: `houmao-srv-ctrl`

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
pixi run python -m houmao.cao.tools.cao_server_launcher --help
houmao-server --help
houmao-srv-ctrl --help
```

## Common Runtime Flags

Useful `start-session` overrides:

- `--cao-base-url http://localhost:<port>` or `http://127.0.0.1:<port>` for a supported launcher-managed loopback CAO endpoint
- `--houmao-base-url http://127.0.0.1:<port>` for the `houmao_server_rest` runtime backend
- `--mailbox-transport filesystem`
- `--mailbox-root <path>`
- `--mailbox-principal-id <principal-id>`
- `--mailbox-address <full-address>`

Useful `build-brain` override:

- `--operator-prompt-mode unattended` to request versioned unattended launch-policy resolution for the built brain instead of the default interactive posture

The paired replacement for `cao-server + cao` is `houmao-server + houmao-srv-ctrl`. Mixed use with raw `cao-server` or raw `cao` is intentionally unsupported for this path. Use [Houmao Server Pair](houmao_server_pair.md) for the contract boundary.

Within that pair, `houmao-srv-ctrl` is split deliberately: top-level `launch` and `install` are Houmao-owned pair commands, while `houmao-srv-ctrl cao ...` is the explicit CAO-compatible namespace.

For pair-managed terminal sessions, the public gateway attach surface also lives on the pair CLI:

- `houmao-srv-ctrl agent-gateway attach --agent <agent-ref> --port <public-port>` for explicit managed-agent targeting
- `houmao-srv-ctrl agent-gateway attach` from inside the target tmux session for current-session attach

Current-session attach requires the target tmux session to publish `AGENTSYS_GATEWAY_ATTACH_PATH` and `AGENTSYS_GATEWAY_ROOT`, and it becomes valid only after the matching managed-agent registration exists on the persisted `api_base_url`.

The runtime `mail` command operates on resumed mailbox-enabled sessions and supports `check`, `send`, and `reply`.

When `start-session` is used with `--json`, unattended sessions may also return:

- `launch_policy_provenance` with the requested mode, detected CLI version, selected strategy id, and whether resolution came from the registry or the transient override env var
- `launch_policy` with the resolved strategy metadata that was attached to the launch plan

Command reminders:

- `mail send` recipients must use full mailbox addresses such as `AGENTSYS-orchestrator@agents.localhost`.
- `mail send` and `mail reply` require body content via `--body-file` or `--body-content`.
- `send-keys` is the low-level CAO control-input surface; use `send-prompt` or `mail` for higher-level runtime-owned turns.

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
