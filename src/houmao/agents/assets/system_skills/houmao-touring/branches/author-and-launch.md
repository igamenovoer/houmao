# Author and Launch Branch

Use this beginner branch when the user wants to create or inspect specialists or profiles, prepare launch defaults, or launch a managed agent.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Route credential readiness to `houmao-credential-mgr` when the user needs to inspect, add, update, log in to, or select a credential before authoring or launch.
3. Route specialist creation, project-profile creation, `create-agent-fast-forward`, and easy-instance launch to `houmao-agent-definition`.
4. When the user needs concrete examples while touring, show the maintained command shapes instead of leaving the namespace implicit:
   - inspect specialists with `houmao-mgr project specialist list` or `houmao-mgr project specialist get --name <name>`
   - inspect profiles with `houmao-mgr project profile list` or `houmao-mgr project profile get --name <name>`
   - launch from a specialist with `houmao-mgr project agents launch --specialist <name> --name <instance-name>`
   - launch from a profile with `houmao-mgr project agents launch --profile <name> --name <instance-name>`
5. Explain the difference between the reusable source and the live runtime:
   - a specialist is a reusable template
   - a project profile is an optional reusable launch-default wrapper
   - a managed agent is the running live instance launched from those sources
6. When the user is unsure, treat profile creation as optional and explain that direct specialist-backed launch is enough for a first run.
7. When the user wants durable launch-time context for future agents, route profile memo-seed work to `houmao-memory-mgr` instead of treating it as ordinary prompt overlay text.
8. For first-run or visible tour launches, advise foreground-first gateway posture for tmux-backed sessions unless the user explicitly asks for background or detached gateway execution:
   - route the detailed launch flags to `houmao-agent-definition`, but carry the rule that agents should not add `--gateway-background` unless the user asked for it
   - explain that the expected visible topology is the managed-agent surface on tmux window `0` and, when a foreground gateway is attached, the gateway sidecar in a non-zero auxiliary tmux window
   - if the launch command runs from a non-interactive caller and reports a `tmux attach-session` command instead of switching into tmux, describe that as tmux handoff behavior, not as detached background gateway execution
   - use supported gateway status fields such as `execution_mode` and `gateway_tmux_window_index` to explain current gateway posture; do not infer posture from tmux names or from lack of automatic tmux attachment
9. After launch, offer stage-aware next actions:
   - send the first normal prompt through `houmao-agent-messaging`
   - inspect running state or screen posture through `houmao-agent-inspect`
   - add or read memo context through `houmao-memory-mgr`
   - send or read mailbox work through `houmao-agent-email-comms`
   - if the live gateway is up and mailbox accounts are already set up, enable or inspect automatic email notification through `houmao-agent-gateway`
   - create reminders through `houmao-agent-gateway`
   - create another specialist or launch a second agent
   - move to advanced loop or isolated workspace guidance only when the user asks for repeated or team coordination

## Guardrails

- Keep profile creation optional; do not force it before launch.
- Do not describe launching an agent as consuming or deleting the specialist source.
- The touring branch does not own detailed specialist credential and launch semantics; keep those on `houmao-agent-definition`.
- Do not point users at top-level `houmao-mgr easy ...`, `houmao-mgr specialists ...`, or raw `.houmao/easy/` inspection when the maintained tour surface is `houmao-mgr project ...`.
- Suggest foreground gateway posture during a tour unless the user explicitly asks for background or detached gateway execution.
- Do not present loop or isolated workspace setup as a beginner launch prerequisite.
