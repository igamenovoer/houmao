# Approved CLI And Tool Names

This repo is using a narrow rename, not the broader lore-driven command vocabulary explored earlier.

## Canonical Names

| Surface | Approved Name | Notes |
| --- | --- | --- |
| Project / distribution | `Houmao` | Repository-facing brand. |
| Primary runtime CLI | `houmao-cli` | Top-level executable only. |
| Runtime module | `gig_agents.agents.realm_controller` | Canonical module path for `python -m`. |
| CAO launcher CLI | `gig-cao-server` | Explicit non-goal: unchanged. |
| Python import root | `gig_agents` | Explicit non-goal: unchanged. |

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
