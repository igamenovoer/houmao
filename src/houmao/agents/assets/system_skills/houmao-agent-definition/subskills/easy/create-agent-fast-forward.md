# Create Agent Fast Forward

Use this subskill when the user wants `create-agent-fast-forward`: one pass from specialist to project profile to launch command.

This workflow creates or selects a specialist, creates or updates a project profile backed by that specialist, initializes default filesystem mailbox readiness, stores mailbox-backed launch defaults on the profile, and prints the launch command that will create the agent mailbox at launch time. It does not launch a live managed agent.

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
4. Determine the managed-agent identity:
   - use supplied `--agent-name` when present;
   - otherwise use a supplied profile-stored managed-agent name when present;
   - otherwise ask for the managed-agent name because the default mailbox identity depends on it.
5. Prepare default project filesystem mailbox readiness:
   - use the active project mailbox root unless the user supplied a different `--mail-root`;
   - run mailbox root initialization before profile creation when the root is not confirmed initialized;
   - derive the ordinary mailbox defaults as principal id `HOUMAO-<agent-name>` and address `<agent-name>@houmao.localhost` unless the user supplied explicit mailbox identity values;
   - do not manually preregister the per-agent account during fast-forward; store the mailbox defaults so the later `project agents launch --profile <profile>` command creates the agent mailbox automatically.
6. Generate `project.profile` with only `name`, `specialist`, and `credential`, then store launch defaults through the maintained profile `create|set` command fields. Store filesystem mailbox posture by default: `--mail-transport filesystem`, `--mail-root <selected-root>`, `--mail-principal-id <principal-id>`, and `--mail-address <address>`.
7. Print the exact launch command by rendering `project.agents.launch`, omitting `--headless` when launch posture is unspecified and TUI/local-interactive launch is supported.
8. Report durable identity facts and stored posture, including mailbox root, principal id, address, and that unspecified launch posture is TUI/local-interactive preferred when supported.
9. Stop. Do not run the launch command.

## Defaults To Store

- specialist name
- project profile name
- managed-agent identity: `--agent-name`, `--agent-id`
- default filesystem mailbox posture: `--mail-transport filesystem`, `--mail-principal-id HOUMAO-<agent-name>`, `--mail-address <agent-name>@houmao.localhost`, `--mail-root <selected-root>`
- workdir: `--workdir`
- prompt mode: omit unless the user explicitly asks to persist one; prompt mode does not imply headless execution. For Kimi, prompt mode is the managed no-question control and should not be replaced with raw `--auto` or `--yolo` launch flags
- launch posture: prefer TUI/local-interactive when supported; store `--headless` only when explicitly requested or required by the selected tool/lane; Kimi is TUI/local-interactive capable here and Gemini remains the selected-tool required-headless exception
- model: `--model`
- reasoning: `--reasoning-level`
- env: repeatable `--env-set NAME=value`
- auth override: `--auth`
- explicit mailbox overrides when supplied: `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`
- gateway posture: `--no-gateway`, `--gateway-port`
- managed prompt header: `--managed-header`, `--no-managed-header`, repeatable `--managed-header-section SECTION=enabled|disabled`
- prompt overlay: `--prompt-overlay-mode`, `--prompt-overlay-text`, `--prompt-overlay-file`
- notifier appendix: `--gateway-mail-notifier-appendix-text`
- memo seed: `--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`

## Command Shapes

```text
<chosen houmao-mgr launcher> project specialist get --name <specialist>
<chosen houmao-mgr launcher> internals config-drafts generate --id project.specialist --intent '{"fields":{"name":"general-kimi","tool":"kimi","credential":"kimi-coding"}}'
<chosen houmao-mgr launcher> project profile get --name <profile>
<chosen houmao-mgr launcher> internals config-drafts generate --id project.profile --intent '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}'
```

Use a top-level `fields` object for config-draft JSON intents. Use `project.specialist` draft fields `name`, `tool`, and `credential`; use `project.profile` draft fields `name`, `specialist`, and `credential`. Do not pass launch defaults, model, env, mailbox, prompt overlay, memo seed, gateway, or credential material fields to config drafts; apply those through maintained project commands when the user supplied them.

Default mailbox root preparation:

```bash
<chosen houmao-mgr launcher> project mailbox init
```

When the user supplies a non-default filesystem mailbox root, initialize that root instead:

```bash
<chosen houmao-mgr launcher> mailbox init --mailbox-root <mail-root>
```

Store the mailbox defaults on the project profile through the maintained profile command:

```bash
<chosen houmao-mgr launcher> project profile create --name <profile> --specialist <specialist> --credential <credential> --agent-name <agent-name> --mail-transport filesystem --mail-root <selected-root> --mail-principal-id HOUMAO-<agent-name> --mail-address <agent-name>@houmao.localhost
```

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
- initialized mailbox root and stored mailbox address/principal id
- stored prompt mode, launch posture, workdir, auth override, mailbox posture, gateway posture, prompt overlay, notifier appendix, memo seed, model, reasoning, and env defaults
- exact launch command

## Guardrails

- Do not launch the managed agent.
- Do not guess missing specialist, profile, tool, credential, managed-agent identity, workdir, gateway, prompt, model, or env inputs.
- Do not persist profile `--headless` or include launch-command `--headless` by default for TUI-capable tools.
- Do not persist profile `--prompt-mode` unless prompt mode is explicit in the user request or recovered explicit context.
- Do not treat unattended prompt mode as evidence that headless launch was requested.
- Do not add raw Kimi `--auto` or `--yolo` launch flags to achieve managed unattended mode.
- When specialist-create tool or credential is omitted, apply Specialist Create Defaulting.
- Do not continue if defaulting finds no Houmao target or no registered credentials; report the suggested fix.
- Do not skip default mailbox setup merely because the user did not mention mailbox; initialize the mailbox root and store default filesystem mailbox posture on the profile.
- Do not manually preregister the same-root ordinary per-agent mailbox address during fast-forward; the later mailbox-backed launch creates the agent mailbox from the stored profile defaults.
- Do not describe the ordinary mailbox address as `HOUMAO-<agent-name>@houmao.localhost`; `HOUMAO-<agent-name>` is the principal id, and `<agent-name>@houmao.localhost` is the address.
- Do not treat `create-agent-fast-forward` as broad live-agent lifecycle work.
