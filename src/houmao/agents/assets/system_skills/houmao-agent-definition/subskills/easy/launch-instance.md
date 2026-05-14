# Launch Easy Instance

Use this subskill only when the user wants to launch one project-easy managed agent from an existing specialist or easy profile.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Use this subskill for `project easy instance launch`, not for general `agents launch`.

## Workflow

1. Determine launch source: `--specialist` or `--profile`.
2. Recover explicit launch inputs from the prompt and recent stated context.
3. For specialist launch, require specialist name and managed-agent name.
4. For profile launch, require profile name.
5. If profile launch lacks a managed-agent name, inspect the profile with `project easy profile get --name <profile>` to see whether it stores one.
6. Run `project easy instance launch`.
7. Report the launched instance identity and command output.
8. Tell the user that broader live-agent management now belongs to `houmao-agent-instance`.

## Command Shapes

```text
<chosen houmao-mgr launcher> project easy instance launch --specialist <specialist> --name <instance> ...
<chosen houmao-mgr launcher> project easy instance launch --profile <profile> [--name <instance>] ...
```

## Common Options

- `--auth`
- `--session-name`
- `--headless`
- `--no-headless`
- `--no-gateway`
- `--gateway-port`
- `--gateway-background` only when the user explicitly requests detached background gateway execution
- gateway TUI timing overrides only when explicitly requested
- `--workdir`
- `--env-set NAME=value|NAME`
- `--mail-transport filesystem|email`
- `--mail-root`
- `--mail-account-dir`
- repeatable `--managed-header-section SECTION=enabled|disabled`

## Notes

- `--specialist` and `--profile` are mutually exclusive.
- Profile-backed launch applies stored profile defaults before direct CLI overrides.
- Profile-backed launch applies any stored memo seed before prompt composition and provider startup.
- Direct specialist-backed launch does not apply a stored memo seed because no reusable profile was selected.
- Launch-time gateway auto-attach is enabled by default unless `--no-gateway` or stored profile posture disables it.
- Default launch-time gateway auto-attach uses foreground same-session auxiliary-window execution when supported.
- A headless managed-agent launch, including a required Gemini headless launch, does not by itself justify `--gateway-background`.
- Unlike `project easy profile create`, launch does not accept declarative mailbox fields such as `--mail-address`, `--mail-principal-id`, `--mail-base-url`, `--mail-jmap-url`, or `--mail-management-url`.
- For launch-time filesystem mailbox support, use `--mail-transport filesystem`, `--mail-root <shared-root>`, and optional `--mail-account-dir <private-path>`.
- When launch derives the ordinary filesystem mailbox identity, `--name` seeds the managed-agent mailbox address and principal id.
- `--mail-account-dir` is a private filesystem mailbox directory outside the shared root that launch symlinks into the shared root.
- If the same ordinary address under the same root was preregistered manually already, launch-time safe registration can fail. For the common ordinary case, let launch own that per-agent address.

## Guardrails

- Do not guess whether the source is a specialist or profile.
- Do not guess specialist name, profile name, or instance name.
- Do not route specialist-backed launch through `agents launch`.
- Do not route profile-backed launch through `agents launch`.
- Do not add `--gateway-background` unless the user explicitly requested background or detached gateway execution.
- Do not teach preregistering the same-root ordinary per-agent mailbox address as the default precursor to mailbox-enabled easy launch.
- Do not describe `--workdir` as changing the source project, specialist source, selected overlay, runtime root, jobs root, or mailbox root.
