# Approved CLI And Tool Names

This repo is using a focused rename, not the broader lore-driven command vocabulary explored earlier.

## Canonical Names

| Surface | Approved Name | Notes |
| --- | --- | --- |
| Project / distribution | `Houmao` | Repository-facing brand. |
| Primary runtime CLI | `houmao-cli` | Top-level executable only. |
| Runtime module | `houmao.agents.realm_controller` | Canonical module path for `python -m`. |
| CAO launcher CLI | `houmao-cao-server` | Canonical launcher executable. |
| Python import root | `houmao` | Canonical import/package root. |

## Commands That Stay Unchanged

Keep the existing supported subcommands:

- `build-brain`
- `start-session`
- `send-prompt`
- `send-keys`
- `mail`
- `stop-session`
- `attach-gateway`
- `detach-gateway`
- `gateway-status`
- `gateway-send-prompt`
- `gateway-interrupt`

## Explicitly Rejected For This Change

Do not adopt broader renames such as `houmao`, `pluck`, `spawn`, `recall`, `command`, `link`, or clone-themed terminology in supported CLIs or contracts unless a later change explicitly approves that scope.
