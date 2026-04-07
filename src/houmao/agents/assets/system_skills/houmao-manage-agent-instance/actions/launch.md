# Launch Agent Instance

Use this action only when the user wants to create one new managed-agent instance from a predefined source. This remains the canonical general lifecycle launch action even though `houmao-manage-specialist` may also front specialist-scoped launch requests.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Determine which launch lane the request actually needs:
   - direct managed launch from a predefined role or preset
   - specialist-backed managed launch from an existing easy specialist
3. Recover the required launch inputs from the current prompt first and recent chat context second when they were stated explicitly.
4. If the source lane or required target inputs are still missing, ask the user in Markdown before proceeding. Prefer a compact table that shows the intended lane and exactly which required fields are still missing.
5. If the request depends on mailbox flags such as `--mail-transport`, `--mail-root`, or `--mail-account-dir`, stop and explain that mailbox-enabled launch is outside this skill's scope.
6. Run the correct launch command.
7. Report the managed-agent identity and launch result returned by the command.

## Command Selection

### Direct Managed Launch

Use this lane when the user wants to launch from a predefined role or preset through the canonical managed-agent lifecycle surface.

Use:

```text
<resolved houmao-mgr launcher> agents launch --agents <selector> --provider <provider> ...
```

Required inputs:

- `--agents`
- `--provider`

Common optional inputs:

- `--agent-name`
- `--agent-id`
- `--auth`
- `--session-name`
- `--headless`
- `--workdir`

Behavior note:

- `--workdir` changes only the launched agent runtime cwd.
- When the selected role or preset resolves from a Houmao project source, source-project overlay resolution stays pinned to that source instead of following `--workdir`.

### Specialist-Backed Managed Launch

Use this lane when the user wants to launch from an existing easy specialist.

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

- Do not guess whether the source should be `agents launch` or `project easy instance launch`.
- Do not invent role selectors, specialist names, provider ids, or instance names.
- Do not proceed with partially inferred launch inputs when the prompt and recent chat context do not state them explicitly; ask the user first.
- Do not route specialist-backed launch through `agents launch`.
- Do not route role/preset launch through `project easy instance launch`.
- Do not describe `--workdir` as changing the source project, preset owner, selected overlay, runtime root, jobs root, or mailbox root.
- Do not include mailbox launch flags in this skill; mailbox-enabled launch is out of scope here.
- Do not treat prompt submission or gateway attach as part of launch completion for this skill.
