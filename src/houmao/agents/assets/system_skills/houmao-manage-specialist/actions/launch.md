# Launch Specialist-Backed Instance

Use this action only when the user wants to launch one easy instance from an existing specialist.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the specialist-backed launch inputs from the current prompt first and recent chat context second when they were stated explicitly.
3. If the specialist name or instance name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need one or two fields.
4. Run `project easy instance launch`.
5. Report the launched instance identity and launch result returned by the command.
6. Tell the user that further agent management should go through `houmao-manage-agent-instance`.

## Command Shape

Use:

```text
<resolved houmao-mgr launcher> project easy instance launch --specialist <specialist> --name <instance> ...
```

Required inputs:

- `--specialist`
- `--name`

Common optional inputs:

- `--auth`
- `--session-name`
- `--headless`
- `--workdir`
- `--env-set NAME=value|NAME`

Behavior note:

- `--workdir` changes only the launched agent runtime cwd.
- The selected easy-project overlay and specialist source stay authoritative even when `--workdir` points outside that project.

If the selected specialist is known to use Gemini, the launch must be headless.

## Guardrails

- Do not guess the specialist name or instance name.
- Do not proceed with partially inferred launch inputs when the prompt and recent chat context do not state them explicitly; ask the user first.
- Do not route specialist-backed launch through `agents launch`.
- Do not describe `--workdir` as changing the source project, specialist source, selected overlay, runtime root, jobs root, or mailbox root.
- Do not imply that the specialist skill is the canonical surface for broader live-agent lifecycle management after launch.
