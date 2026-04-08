# Launch Specialist- Or Profile-Backed Instance

Use this action only when the user wants to launch one easy instance from an existing specialist or an existing easy profile.

## Workflow

1. Determine whether the launch source is `specialist` or `profile`.
2. If that launch-source kind is still ambiguous after checking the prompt and recent chat context, ask the user before proceeding.
3. Use the `houmao-mgr` launcher already chosen by the top-level skill.
4. Recover the launch inputs from the current prompt first and recent chat context second when they were stated explicitly.
5. If the launch source is `specialist` and the specialist name or instance name is still missing, ask the user in Markdown before proceeding. Prefer a short bullet list when you only need one or two fields.
6. If the launch source is `profile` and the profile name is still missing, ask the user before proceeding.
7. If the launch source is `profile` and no instance name was stated, inspect the profile first with `project easy profile get --name <profile>` to see whether it stores a default managed-agent name. Ask for `--name` only if the profile does not store one.
8. Run `project easy instance launch`.
9. Report the launched instance identity and launch result returned by the command.
10. Tell the user that further agent management should go through `houmao-manage-agent-instance`.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project easy instance launch --specialist <specialist> --name <instance> ...
<chosen houmao-mgr launcher> project easy instance launch --profile <profile> [--name <instance>] ...
```

Required inputs:

- `--specialist` and `--name` for specialist-backed launch
- `--profile` for profile-backed launch
- `--name` for profile-backed launch only when the selected profile does not already store a default managed-agent name

Common optional inputs:

- `--auth`
- `--session-name`
- `--headless`
- `--no-headless`
- `--no-gateway`
- `--gateway-port`
- `--workdir`
- `--env-set NAME=value|NAME`
- `--mail-transport filesystem|email`
- `--mail-root`
- `--mail-account-dir`

Behavior note:

- `--specialist` and `--profile` are mutually exclusive.
- `--workdir` changes only the launched agent runtime cwd.
- The selected easy-project overlay and specialist source stay authoritative even when `--workdir` points outside that project.
- Profile-backed launch applies stored profile defaults before direct CLI overrides.
- `--no-gateway` and `--gateway-port` cannot be combined.
- `--mail-account-dir` is only supported with `--mail-transport filesystem`.
- `--mail-transport filesystem` requires `--mail-root`.
- `--mail-transport email` is not implemented on this surface.

If the selected specialist or selected profile source is known to use Gemini, the launch must be headless.

## Guardrails

- Do not guess whether the user wants to launch from a specialist or from an easy profile.
- Do not guess the specialist name, profile name, or instance name.
- Do not proceed with partially inferred launch inputs when the prompt and recent chat context do not state them explicitly; ask the user first.
- Do not route specialist-backed launch through `agents launch`.
- Do not route profile-backed launch through `agents launch`.
- Do not describe `--workdir` as changing the source project, specialist source, selected overlay, runtime root, jobs root, or mailbox root.
- Do not imply that the specialist skill is the canonical surface for broader live-agent lifecycle management after launch.
