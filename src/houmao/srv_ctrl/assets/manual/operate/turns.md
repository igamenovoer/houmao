# Submit and Follow a Turn

For an ordinary turn with a live gateway, prefer `gateway prompt` with its default `ready-only` policy. Without a live gateway, use scoped `prompt`. Treat a readiness refusal as a reason to wait and inspect. Keep the chosen delivery policy on any retry.

For a tracked headless run, use `turn submit`, keep the returned turn ID, and check `turn status` or `turn events` for that turn. For other modes, verify the result through the applicable state or the requested artifact. A receipt can establish acceptance or native handoff before the provider completes the work.

After a timeout or lost receipt, inspect the same target and any existing request or turn evidence before sending again. Use scoped `interrupt` when asked to cancel work and check the resulting turn state. `houmao-mgr agents single --agent-id "$agent_id" prompt --help` shows the command syntax. [Gateway Prompt Admission](https://igamenovoer.github.io/houmao/reference/cli/agents-gateway/#prompt) · [Managed Headless Turns](https://igamenovoer.github.io/houmao/reference/cli/agents-turn/)
