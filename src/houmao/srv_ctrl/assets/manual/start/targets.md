# Select the Right Agent Target

Use this before inspecting or changing one worker. The agent ID identifies the target. The runtime checks which operations the caller can perform.

- As an operator, start with `houmao-mgr agents global list` or `project agents list` for a known project. Match the worker to the request and use its returned ID with `houmao-mgr agents single --agent-id "$agent_id" state`. Resolve ambiguity before acting.
- For managed-self work, run `houmao-mgr --print-json agents self identity` in the current managed tmux session. Use `agents self` only after it returns the expected identity. Peer work still needs an explicit target.
- A worker launched through an execution profile has a saved owner route. For an external communication reference, use `houmao-mgr agents external verify --agent-name "$alias"` when you need current remote identity. Address supported communications by alias and leave lifecycle operations to its owner.

Before acting, check that the reported identity and ownership match the task. For syntax, run `houmao-mgr agents --help`. [External Agents](https://igamenovoer.github.io/houmao/reference/cli/agents-external/) · [Execution Contexts](https://igamenovoer.github.io/houmao/reference/run-phase/execution-contexts/)
