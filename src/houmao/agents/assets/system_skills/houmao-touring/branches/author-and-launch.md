# Author And Launch Branch

Use this branch when the user wants to create or inspect specialists or profiles, or launch another managed agent.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Route specialist creation, easy-profile creation, and easy-instance launch to `houmao-specialist-mgr`.
3. When the user needs concrete examples while touring, show the maintained command shapes instead of leaving the namespace implicit:
   - inspect specialists with `houmao-mgr project easy specialist list` or `houmao-mgr project easy specialist get --name <name>`
   - inspect profiles with `houmao-mgr project easy profile list` or `houmao-mgr project easy profile get --name <name>`
   - launch from a specialist with `houmao-mgr project easy instance launch --specialist <name> --name <instance-name>`
   - launch from a profile with `houmao-mgr project easy instance launch --profile <name> --name <instance-name>`
4. Explain the difference between the reusable source and the live runtime:
   - a specialist is a reusable template
   - an easy profile is an optional reusable launch-default wrapper
   - a managed agent is the running live instance launched from those sources
5. When the user is unsure, treat profile creation as optional and explain that direct specialist-backed launch is enough for a first run.
6. For first-run or visible tour launches, advise foreground-first gateway posture for tmux-backed sessions unless the user explicitly asks for background or detached gateway execution:
   - route the detailed launch flags to `houmao-specialist-mgr`, but carry the rule that agents should not add `--gateway-background` unless the user asked for it
   - explain that the expected visible topology is the managed-agent surface on tmux window `0` and, when a foreground gateway is attached, the gateway sidecar in a non-zero auxiliary tmux window
   - if the launch command runs from a non-interactive caller and reports a `tmux attach-session` command instead of switching into tmux, describe that as tmux handoff behavior, not as detached background gateway execution
   - use supported gateway status fields such as `execution_mode` and `gateway_tmux_window_index` to explain current gateway posture; do not infer posture from tmux names or from lack of automatic tmux attachment
7. After launch, offer the next likely branches:
   - send a normal prompt
   - watch live gateway or TUI state
   - send mailbox work
   - if the live gateway is up and mailbox accounts are already set up, enable automatic email notification so the agent can check unread mail automatically
   - create reminders
   - explore advanced pairwise agent-loop creation
   - create another specialist or launch another agent

## Guardrails

- Do not force profile creation before launch.
- Do not describe launching an agent as consuming or deleting the specialist source.
- Do not pretend the touring branch owns the detailed specialist credential and launch semantics; keep those on `houmao-specialist-mgr`.
- Do not point users at top-level `houmao-mgr easy ...`, `houmao-mgr specialists ...`, or raw `.houmao/easy/` inspection when the maintained tour surface is `houmao-mgr project easy ...`.
- Do not suggest background gateway launch or attach during a tour unless the user explicitly asks for background or detached gateway execution.
