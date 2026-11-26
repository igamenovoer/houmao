# Change an Agent's Lifecycle

Start local lifecycle management with `houmao-mgr project agents launch` using a project profile or specialist. Record the returned agent ID. Use scoped `interrupt` to cancel a turn and `agents single ... stop` when the body should exit.

Use `refresh --check` to inspect native skill and MCP freshness. Use `refresh` for a supported reload that keeps the running conversation. Use selected-agent `relaunch` to restart a supported instance or revive a recoverable one. It keeps the recorded identity and run mode. Choose the provider conversation policy explicitly if continuity matters. Use `project agents launch` for a new instance or to apply changed birth settings.

If you manage a session adopted by an earlier release, use that release to run `houmao-mgr agents single --agent-id <id> gateway detach` before upgrading. Leave the manual session running and keep its files if you want to continue it outside Houmao. A normal `stop` can terminate the provider pane.

Verify the resulting state. After stopping, check the same ID in `agents global list --state all`. For artifact removal, inspect the plan with selected-agent `cleanup session --dry-run` before applying it. `houmao-mgr agents single --agent-id "$agent_id" relaunch --help` shows the conversation options. [Session Lifecycle](https://igamenovoer.github.io/houmao/reference/run-phase/session-lifecycle/) · [Degraded and Stale Recovery](https://igamenovoer.github.io/houmao/reference/run-phase/degraded-stale-recovery/)
