# houmao-mgr agents mailbox

Late filesystem mailbox registration for local managed agents. These commands register, inspect, or remove filesystem mailbox bindings on existing local managed agents without requiring relaunch.

```
houmao-mgr agents mailbox [OPTIONS] COMMAND [ARGS]...
```

## Commands

### `register`

Register one filesystem mailbox binding for an existing local managed agent.

```
houmao-mgr agents mailbox register [OPTIONS]
```

| Option | Description |
|---|---|
| `--mailbox-root DIRECTORY` | Filesystem mailbox root override. Defaults to `AGENTSYS_GLOBAL_MAILBOX_DIR` or the shared Houmao mailbox root. |
| `--principal-id TEXT` | Optional mailbox principal id override. Defaults from the managed-agent identity. |
| `--address TEXT` | Optional full mailbox address override. Defaults from the managed-agent identity. |
| `--mode [safe\|force\|stash]` | Filesystem mailbox registration mode. Default: `safe`. |
| `--yes` | Confirm destructive replacement without prompting. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. Do not include the `AGENTSYS-` prefix. |

When `register` would replace existing shared mailbox state, it prompts before destructive replacement on interactive terminals. In automation or other non-interactive contexts, rerun with `--yes` to confirm the overwrite explicitly.

### `unregister`

Remove one filesystem mailbox binding from an existing local managed agent.

```
houmao-mgr agents mailbox unregister [OPTIONS]
```

| Option | Description |
|---|---|
| `--mode [deactivate\|purge]` | Filesystem mailbox deregistration mode. Default: `deactivate`. |
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

### `status`

Report late mailbox registration posture for one local managed agent.

```
houmao-mgr agents mailbox status [OPTIONS]
```

| Option | Description |
|---|---|
| `--agent-id TEXT` | Authoritative managed-agent id. |
| `--agent-name TEXT` | Raw creation-time friendly managed-agent name. |

## Workflow

The preferred local serverless mailbox workflow is:

1. `houmao-mgr mailbox init --mailbox-root <path>`
2. `houmao-mgr agents launch ...` or `houmao-mgr agents join ...`
3. `houmao-mgr agents mailbox register --agent-name <name> --mailbox-root <path>`
4. `houmao-mgr agents mail ...`

For supported tmux-backed managed sessions, including sessions adopted through `houmao-mgr agents join`, `agents mailbox register` and `agents mailbox unregister` refresh the live mailbox projection without requiring relaunch. That remains true even when a joined session is controllable but non-relaunchable, as long as Houmao can still update the session manifest and the owning tmux live mailbox projection safely.

## See Also

- [houmao-mgr](houmao-mgr.md) — parent CLI reference
- [agents mail](agents-mail.md) — managed-agent mailbox follow-up commands
- [Mailbox Reference](../mailbox/index.md) — mailbox subsystem details
