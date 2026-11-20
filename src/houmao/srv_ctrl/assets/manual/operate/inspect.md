# Inspect an Agent

Use this when asked whether a worker is running, ready for another prompt, or making progress. Start with `houmao-mgr --print-json agents single --agent-id "$agent_id" state` for a selected worker. Use `agents self state` from a verified managed session. Keep the reported ID, run mode, and state together.

- For a tracked headless run, read `turn status` and `turn events` for its turn ID. The worker process can exit while those records remain available.
- For a TUI, use `gateway tui state` when the gateway is attached. Read readiness and tracked turn posture before sending more work.
- For a service, check the native connection and the request it reports. For Web, check readiness and turn evidence for the bound browser session. Use the mode-specific state detail when the summary is insufficient.

Report the strongest observation you have. A live process establishes liveness. Confirm progress or completion from the matching turn or requested artifact. `houmao-mgr agents single --agent-id "$agent_id" state --help` shows the command syntax. [Managed-Agent State](https://igamenovoer.github.io/houmao/reference/managed_agent_api/#detailed-state)
