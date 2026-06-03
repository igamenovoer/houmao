# Create Agent Fast Forward

Use this subskill when the user wants `create-agent-fast-forward`: one pass from specialist to project profile to launch command.

This workflow creates or selects a specialist, creates or updates a project profile backed by that specialist, stores supplied launch defaults on the profile, and prints the launch command. It does not launch a live managed agent.

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
   - otherwise create one with `project specialist create`;
   - when creating one, resolve tool and credential from the current prompt, nearby explicit context, or Specialist Create Defaulting.
2. Determine the project profile name:
   - use the user-provided profile name;
   - otherwise ask for it.
3. Determine profile operation:
   - create when the profile does not exist or the user asks for a new profile;
   - set when updating an existing profile;
   - create `--yes` only when the user explicitly wants same-name replacement.
4. Generate `project.profile` with only `name`, `specialist`, and `credential`, then store any supplied launch defaults through the maintained profile `create|set` command fields.
5. Print the exact launch command by rendering `project.agents.launch`, omitting `--headless` when launch posture is unspecified and TUI/local-interactive launch is supported.
6. Report durable identity facts and stored posture, including that unspecified launch posture is TUI/local-interactive preferred when supported.
7. Stop. Do not run the launch command.

## Defaults To Store When Supplied

- specialist name
- project profile name
- managed-agent identity: `--agent-name`, `--agent-id`
- workdir: `--workdir`
- prompt mode: omit unless the user explicitly asks to persist one; prompt mode does not imply headless execution
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
<chosen houmao-mgr launcher> project specialist get --name <specialist>
<chosen houmao-mgr launcher> internals config-drafts generate --id project.specialist --intent '{"fields":{"name":"general-kimi","tool":"claude","credential":"kimi-coding"}}'
<chosen houmao-mgr launcher> project profile get --name <profile>
<chosen houmao-mgr launcher> internals config-drafts generate --id project.profile --intent '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}'
```

Use a top-level `fields` object for config-draft JSON intents. Use `project.specialist` draft fields `name`, `tool`, and `credential`; use `project.profile` draft fields `name`, `specialist`, and `credential`. Do not pass launch defaults, model, env, mailbox, prompt overlay, memo seed, gateway, or credential material fields to config drafts; apply those through maintained project commands when the user supplied them.

Report this launch command without executing it:

```bash
<chosen houmao-mgr launcher> project agents launch --profile <profile>
```

If the profile does not store an agent name, include the managed-agent name explicitly.

```bash
<chosen houmao-mgr launcher> project agents launch --profile <profile> --name <agent-name>
```

## Output

Report:

- specialist name
- project profile name
- intended managed-agent name or agent id when known
- stored prompt mode, launch posture, workdir, auth override, mailbox posture, gateway posture, prompt overlay, notifier appendix, memo seed, model, reasoning, and env defaults when present
- exact launch command

## Guardrails

- Do not launch the managed agent.
- Do not guess missing specialist, profile, tool, credential, identity, workdir, mailbox, gateway, prompt, model, or env inputs.
- Do not persist profile `--headless` or include launch-command `--headless` by default for TUI-capable tools.
- Do not persist profile `--prompt-mode` unless prompt mode is explicit in the user request or recovered explicit context.
- Do not treat unattended prompt mode as evidence that headless launch was requested.
- When specialist-create tool or credential is omitted, apply Specialist Create Defaulting.
- Do not continue if defaulting finds no Houmao target or no registered credentials; report the suggested fix.
- Do not manually preregister a same-root ordinary per-agent mailbox address when profile defaults or project launch can own ordinary launch-time mailbox bootstrap.
- Do not treat `create-agent-fast-forward` as broad live-agent lifecycle work.
