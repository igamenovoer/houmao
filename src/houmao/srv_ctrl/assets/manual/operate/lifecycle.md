# Change an Agent's Lifecycle

Start from the agent's state and the requested effect. Use `agents self join` inside an existing supported TUI session when asked to bring it under management. Record its ID after adoption. Use scoped `interrupt` to cancel a turn and `agents single ... stop` when the body should exit.

Use `refresh --check` to inspect native skill and MCP freshness. Use `refresh` for a supported reload that keeps the running conversation. Use selected-agent `relaunch` to restart a supported instance or revive a recoverable one. It keeps the recorded identity and run mode. Choose the provider conversation policy explicitly if continuity matters. Use `project agents launch` for a new instance or to apply changed birth settings.

Verify the resulting state. After stopping, check the same ID in `agents global list --state all`. For artifact removal, inspect the plan with selected-agent `cleanup session --dry-run` before applying it. `houmao-mgr agents single --agent-id "$agent_id" relaunch --help` shows the conversation options. [Session Lifecycle](https://igamenovoer.github.io/houmao/reference/run-phase/session-lifecycle/) · [Degraded and Stale Recovery](https://igamenovoer.github.io/houmao/reference/run-phase/degraded-stale-recovery/)
