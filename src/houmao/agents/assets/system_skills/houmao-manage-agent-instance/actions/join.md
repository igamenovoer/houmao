# Join Agent Instance

Use this action only when the user wants Houmao to adopt one already-running supported provider session as a managed-agent instance.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the join inputs from the current prompt first and recent chat context second when they were stated explicitly.
3. If the managed-agent name is still missing, ask the user before proceeding.
4. If the request is for headless join, require the provider and at least one recorded `--launch-args` value before proceeding.
5. Run `agents join`.
6. Report the adopted managed-agent identity and resulting lifecycle state returned by the command.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> agents join --agent-name <name> ...
```

Headless join requires:

- `--headless`
- `--provider`
- one or more `--launch-args`

Other optional inputs:

- `--agent-id`
- `--working-directory`
- repeatable `--launch-env NAME=value|NAME`
- `--resume-id`
- `--no-install-houmao-skills`

## Guardrails

- Do not guess the managed-agent name, provider, or launch args for headless join.
- Do not treat join as mailbox registration, gateway attach, or prompt submission.
- Do not claim that join restarts the live provider process; it adopts the existing session into Houmao control.
- Do not route join work through launch commands.
