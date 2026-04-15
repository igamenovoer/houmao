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
10. Tell the user that further agent management should go through `houmao-agent-instance`.

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
- `--gateway-background` only when the user explicitly requests detached background gateway execution
- `--gateway-tui-watch-poll-interval-seconds`, `--gateway-tui-stability-threshold-seconds`, `--gateway-tui-completion-stability-seconds`, `--gateway-tui-unknown-to-stalled-timeout-seconds`, `--gateway-tui-stale-active-recovery-seconds`, or `--gateway-tui-final-stable-active-recovery-seconds` only when the user explicitly requests custom gateway TUI tracking timing
- `--workdir`
- `--env-set NAME=value|NAME`
- `--mail-transport filesystem|email`
- `--mail-root`
- `--mail-account-dir`
- repeatable `--managed-header-section SECTION=enabled|disabled`

Behavior note:

- `--specialist` and `--profile` are mutually exclusive.
- `--workdir` changes only the launched agent runtime cwd.
- The selected easy-project overlay and specialist source stay authoritative even when `--workdir` points outside that project.
- Profile-backed launch applies stored profile defaults before direct CLI overrides.
- Profile-backed launch also applies any stored memo seed before prompt composition and provider startup. Direct specialist-backed launch does not apply a stored memo seed because no reusable profile was selected.
- `--managed-header-section` is a one-shot managed-header section override and never rewrites the selected easy profile.
- `--no-gateway` and `--gateway-port` cannot be combined.
- `--no-gateway` cannot be combined with any `--gateway-tui-*` timing override.
- Launch-time gateway auto-attach is enabled by default unless `--no-gateway` or stored profile posture disables it.
- Default launch-time gateway auto-attach uses foreground same-session auxiliary-window execution when supported; use `--gateway-background` only when the user explicitly asks for background gateway execution, detached gateway process execution, or avoiding a gateway tmux window.
- One-shot `--gateway-tui-*` values are positive seconds, tune only the gateway sidecar's TUI tracking, and never rewrite the selected easy profile.
- Managed-agent `--headless` or `--no-headless` posture is separate from gateway sidecar foreground/background execution. A headless managed-agent launch, including a required Gemini headless launch, does not by itself justify `--gateway-background`.
- `--mail-account-dir` is only supported with `--mail-transport filesystem`.
- `--mail-transport filesystem` requires `--mail-root`.
- `--mail-transport email` is not implemented on this surface.

Mailbox behavior note:

- Unlike `project easy profile create`, this launch command does not accept declarative mailbox fields such as `--mail-address`, `--mail-principal-id`, `--mail-base-url`, `--mail-jmap-url`, or `--mail-management-url`.
- For launch-time filesystem mailbox support, use only `--mail-transport filesystem`, `--mail-root <shared-root>`, and optional `--mail-account-dir <private-path>`.
- When mailbox-enabled launch derives the ordinary filesystem mailbox identity itself, `--name` seeds the managed-agent mailbox address and principal id for that launch.
- Omitting `--mail-account-dir` means launch-owned mailbox bootstrap uses the standard in-root mailbox path under the shared root.
- `--mail-account-dir` is an optional private filesystem mailbox directory that the launch symlinks into the shared root, so it must live outside `--mail-root`.
- If the same ordinary address under that same root was preregistered manually already, launch-time safe registration can fail. For that common case, let the later launch own the per-agent address instead of preregistering it.

If the selected specialist or selected profile source is known to use Gemini, the launch must be headless.

## Guardrails

- Do not guess whether the user wants to launch from a specialist or from an easy profile.
- Do not guess the specialist name, profile name, or instance name.
- Do not proceed with partially inferred launch inputs when the prompt and recent chat context do not state them explicitly; ask the user first.
- Do not route specialist-backed launch through `agents launch`.
- Do not route profile-backed launch through `agents launch`.
- Do not add `--gateway-background` unless the user explicitly requested background or detached gateway execution.
- Do not present `--mail-address`, `--mail-principal-id`, `--mail-base-url`, `--mail-jmap-url`, or `--mail-management-url` as supported `project easy instance launch` flags.
- Do not describe `--mail-account-dir` as the already-registered shared-root mailbox directory; it is a private filesystem mailbox directory outside the shared root.
- Do not teach preregistering the same-root ordinary per-agent mailbox address as the default precursor to mailbox-enabled easy launch.
- Do not describe `--workdir` as changing the source project, specialist source, selected overlay, runtime root, jobs root, or mailbox root.
- Do not imply that the specialist skill is the canonical surface for broader live-agent lifecycle management after launch.
