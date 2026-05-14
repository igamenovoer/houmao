# Create Agent Fast Forward

Use this subskill when the user wants `create-agent-fast-forward`: one pass from specialist to easy profile to launch command.

This workflow creates or selects a specialist, creates or updates an easy profile backed by that specialist, stores supplied launch defaults on the profile, and prints the launch command. It does not launch a live managed agent.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Read [../common/profile-lanes.md](../common/profile-lanes.md).
- Read [../common/credential-routing.md](../common/credential-routing.md).
- Use [specialists.md](specialists.md) for the specialist create or select step.
- Use [profiles.md](profiles.md) for the profile create or update step.

## Workflow

1. Determine the intended specialist:
   - use an existing specialist when the user named one;
   - otherwise create one with `project easy specialist create`;
   - when creating one, resolve tool and credential from the current prompt, nearby explicit context, or Specialist Create Defaulting.
2. Determine the easy profile name:
   - use the user-provided profile name;
   - otherwise ask for it.
3. Determine profile operation:
   - create when the profile does not exist or the user asks for a new profile;
   - set when updating an existing profile;
   - create `--yes` only when the user explicitly wants same-name replacement.
4. Store all supplied launch defaults on the easy profile, omitting stored headless posture unless the user explicitly asked for headless or the selected tool/lane requires it.
5. Print the exact launch command, omitting `--headless` when launch posture is unspecified and TUI/local-interactive launch is supported.
6. Report durable identity facts and stored posture, including that unspecified launch posture is TUI/local-interactive preferred when supported.
7. Stop. Do not run the launch command.

## Defaults To Store When Supplied

- specialist name
- easy profile name
- managed-agent identity: `--agent-name`, `--agent-id`
- workdir: `--workdir`
- prompt mode: default to unattended unless the user requests `as_is`; prompt mode does not imply headless execution
- launch posture: prefer TUI/local-interactive when supported; store `--headless` only when explicitly requested or required by the selected tool/lane
- model: `--model`
- reasoning: `--reasoning-level`
- env: repeatable `--env-set NAME=value`
- auth override: `--auth`
- mailbox posture: `--mail-transport`, `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`
- gateway posture: `--no-gateway`, `--gateway-port`
- managed prompt header: `--managed-header`, `--no-managed-header`, repeatable `--managed-header-section SECTION=enabled|disabled`
- prompt overlay: `--prompt-overlay-mode`, `--prompt-overlay-text`, `--prompt-overlay-file`
- notifier appendix: `--gateway-mail-notifier-appendix-text`
- memo seed: `--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`

## Command Shapes

```text
<chosen houmao-mgr launcher> project easy specialist get --name <specialist>
<chosen houmao-mgr launcher> project easy specialist create --name <specialist> --tool <tool> ...
<chosen houmao-mgr launcher> project easy profile get --name <profile>
<chosen houmao-mgr launcher> project easy profile create --name <profile> --specialist <specialist> ...
<chosen houmao-mgr launcher> project easy profile set --name <profile> ...
```

Report this launch command without executing it:

```text
<chosen houmao-mgr launcher> project easy instance launch --profile <profile>
```

If the profile does not store an agent name, show the explicit form:

```text
<chosen houmao-mgr launcher> project easy instance launch --profile <profile> --name <managed-agent-name>
```

## Output

Report:

- specialist name
- easy profile name
- intended managed-agent name or agent id when known
- stored prompt mode, launch posture, workdir, auth override, mailbox posture, gateway posture, prompt overlay, notifier appendix, memo seed, model, reasoning, and env defaults when present
- exact launch command

## Guardrails

- Do not launch the managed agent.
- Do not guess missing specialist, profile, tool, credential, identity, workdir, mailbox, gateway, prompt, model, or env inputs.
- Do not persist profile `--headless` or include launch-command `--headless` by default for TUI-capable tools.
- Do not treat unattended prompt mode as evidence that headless launch was requested.
- When specialist-create tool or credential is omitted, apply Specialist Create Defaulting.
- Do not continue if defaulting finds no Houmao target or no registered credentials; report the suggested fix.
- Do not manually preregister a same-root ordinary per-agent mailbox address when profile defaults or easy launch can own ordinary launch-time mailbox bootstrap.
- Do not treat `create-agent-fast-forward` as broad live-agent lifecycle work.
