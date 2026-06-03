# Join Agent Instance

Use this action only when the user wants Houmao to adopt one already-running supported provider session as a managed-agent instance.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the join inputs from the current prompt first and recent chat context second when they were stated explicitly.
3. If the managed-agent name is still missing, ask the user in Markdown before proceeding.
4. If the request is for headless join and the provider or `--launch-args` values are still missing, ask the user in Markdown for those missing fields before proceeding.
5. Build the direct `agents self join` command from explicit inputs only.
6. Run the direct command.
7. Report the adopted managed-agent identity and resulting lifecycle state returned by the command.

## Command Shape

Run the direct join command:

```bash
<chosen houmao-mgr launcher> agents self join --agent-name <managed-agent-name> [--agent-id <agent-id>] [--workdir <dir>]
<chosen houmao-mgr launcher> agents self join --agent-name <managed-agent-name> --headless --provider <provider> --launch-args <arg>
```

Headless join requires:

- `--headless`
- `--provider`
- one or more `--launch-args`

Other optional inputs:

- `--agent-id`
- `--workdir`
- repeatable `--launch-env NAME=value|NAME`
- `--resume-id`
- `--no-install-houmao-skills`

## Guardrails

- Do not guess the managed-agent name, provider, or launch args for headless join.
- Do not continue with headless join from partial assumptions about provider or launch args.
- Do not treat join as mailbox registration, gateway attach, or prompt submission.
- Do not claim that join restarts the live provider process; it adopts the existing session into Houmao control.
- Do not route join work through launch commands.
- Do not add provider, posture, launch args, launch env, or resume flags unless the user explicitly supplied them or headless join requires them.
