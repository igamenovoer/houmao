# Tmux Server Choices

Save `--tmux-server` in either project profile family or supply it on `project agents launch` for one launch. Houmao resolves the choice in the execution owner's context.

| Choice | Launch Behavior |
| --- | --- |
| `user-default` | Select the execution account's native default tmux socket, independent of the enclosing session. Start a server there if needed. |
| `houmao-default` | Select the execution owner's shared Houmao socket recorded in the shared registry. Houmao records and starts this server lazily as needed. |
| `new` | Allocate and start a private server for the new agent instance. |
| `socket` | Select a running server at an absolute owner-side path supplied with `--tmux-socket-path`. A missing server or a conflict with the execution context is a launch error. |

A one-shot selector takes precedence over the saved choice. If both are absent, Houmao uses the admitted executor socket or explicit local scope, then the enclosing tmux server, then the account's native default. An explicit choice must respect a socket pinned by the execution binding. `--session-name` names a session on the selected server. Relaunch uses the socket recorded at birth.

Saving a selector affects future launches. Inspect `defaults.posture.tmux` with the matching profile `get` command. A `set` that omits tmux flags preserves the block. Supplying a mode replaces the block, and `--clear-tmux-server` removes it to restore launch-time fallback.
