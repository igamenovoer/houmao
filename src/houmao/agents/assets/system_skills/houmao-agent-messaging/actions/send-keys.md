# Send Raw Control Input

Use this action only when the user needs exact raw control input delivered through a live gateway and the work must not be treated as a prompt turn.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector and raw key sequence from the current prompt first and recent chat context second when they were stated explicitly.
3. If the target selector or key sequence is still missing, ask the user in Markdown before proceeding.
4. When the current context does not already confirm live gateway availability, run `agents gateway status` first.
5. Use `agents gateway send-keys` for the exact raw key delivery.
6. Use `agents gateway tui state|history` when the task needs the exact raw gateway-owned TUI state before or after the key sequence.
7. If the caller is already operating through the pair-managed HTTP API, use `POST /houmao/agents/{agent_ref}/gateway/control/send-keys`.
8. Report the submitted sequence and any relevant visible gateway-owned TUI outcome.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents gateway send-keys --agent-name <name> --sequence "<[Escape]>"
```

Common raw-input cases:

- slash-command menus
- arrow navigation
- `Escape`
- partial typing without an implicit final `Enter`
- exact literal sequences with `--escape-special-keys`

## Guardrails

- Do not redirect raw control-input work to `agents prompt`.
- Do not claim that `agents gateway send-keys` appends an implicit trailing `Enter`.
- Do not invent key names or edit the requested sequence unless the user explicitly asked for that transformation.
- Do not use `send-keys` for mailbox work or transport-neutral interrupt.
- Do not assume raw control input is safe when the live gateway is unavailable.
