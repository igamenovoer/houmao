# Project Profiles

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this subskill when the user wants to create, inspect, update, list, replace, or remove one specialist-backed project profile through `project profile ...`.

## Preconditions

- Read [../../references/common/launcher.md](../../references/common/launcher.md).
- Read [../../references/common/missing-inputs.md](../../references/common/missing-inputs.md).
- Read [../../references/common/profile-lanes.md](../../references/common/profile-lanes.md).
- Read [../../references/common/credential-routing.md](../../references/common/credential-routing.md) when auth overrides are involved.
- Confirm the profile lane is specialist-backed project profile, not a native launch dossier.

## Actions

- List profiles: no name required.
- Get profile: require `--name`.
- Create profile: require `--name` and `--specialist`.
- Set profile: require `--name` and at least one update or clear field.
- Replace profile: use `create --yes` only when the user intends same-name replacement.
- Remove profile: require `--name`.

## Command Shapes

```text
<chosen houmao-mgr launcher> project profile list
<chosen houmao-mgr launcher> project profile get --name <name>
<chosen houmao-mgr launcher> project profile remove --name <profile>
```

For `create`, same-name replacement, and profile config-document preparation, use the CLI-owned config draft before running the maintained command:

```text
<chosen houmao-mgr launcher> internals config-drafts generate --id project.profile --intent '{"fields":{"name":"reviewer-fast","specialist":"reviewer","credential":"reviewer-creds"}}'
```

The `project.profile` config draft is intentionally minimal. Its JSON intent must contain a top-level `fields` object whose only draft fields are `name`, `specialist`, and `credential`. The draft fixes the project profile lane and specialist source kind, then records the credential as the profile auth reference. For model, env, mailbox, launch posture, managed header, prompt overlay, notifier appendix, memo seed, or other stored defaults, use the maintained `project profile create|set` fields directly instead of adding them to the draft intent.

For `set`, keep the maintained patch command explicit and include only the user-requested mutation fields.

## Stored Defaults

Project profiles may store:

- identity: `--agent-name`, `--agent-id`
- working directory: `--workdir`
- auth override: `--auth`
- model posture: `--model`, `--reasoning-level`
- prompt mode: `--prompt-mode unattended|as_is`
- durable env: repeatable `--env-set NAME=value`
- mailbox defaults: `--mail-transport filesystem|stalwart`, `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`
- run mode: `--mode headless|service|tui|web` at `defaults.posture.mode`
- tmux server: `--tmux-server` and, for `socket`, `--tmux-socket-path`
- gateway posture: `--no-gateway`, `--gateway-port`
- managed prompt header: `--managed-header`, `--no-managed-header`, repeatable `--managed-header-section SECTION=enabled|disabled`
- prompt overlay: `--prompt-overlay-mode append|replace`, `--prompt-overlay-text`, `--prompt-overlay-file`
- gateway mail-notifier default: `--gateway-mail-notifier-appendix-text`
- memo seed: `--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`

## Saved Tmux Server

See [Tmux Server Choices](../../references/common/tmux-server.md) for the four modes and launch precedence. Save the choice through `create` or `set` and verify the resulting `defaults.posture.tmux` with `get`.

```bash
houmao-mgr project profile create --name worker --specialist researcher --tmux-server houmao-default
houmao-mgr project profile set --name worker --tmux-server socket --tmux-socket-path /run/user/1000/research.sock
houmao-mgr project profile get --name worker
```

## Default Run Mode

Store `--mode` when the user specifies a supported mode. Omit it to let the project choose the tool default described in [Profile Lanes](../../references/common/profile-lanes.md#run-modes). Kimi-backed profiles default to TUI. A launch-level `--mode` selects a different mode for one instance.

For Kimi-backed profiles, use `--prompt-mode unattended` as the managed no-question control. Do not store raw Kimi `--auto` or `--yolo` launch arguments to achieve unattended TUI behavior.

## Clear Fields

`profile set` may clear:

- `--clear-agent-name`
- `--clear-agent-id`
- `--clear-workdir`
- `--clear-auth`
- `--clear-model`
- `--clear-reasoning-level`
- `--clear-prompt-mode`
- `--clear-env`
- `--clear-mailbox`
- `--clear-mode`
- `--clear-tmux-server`
- `--clear-managed-header`
- `--clear-managed-header-section SECTION`
- `--clear-managed-header-sections`
- `--clear-prompt-overlay`
- `--clear-gateway-mail-notifier-appendix`
- `--clear-memo-seed`

## Rules

- Use `project profile set` for ordinary edits.
- An omitted tmux option preserves the selector on `set`. A new choice replaces it and `--clear-tmux-server` restores launch-time fallback.
- Use `project profile create --yes` only for intended same-name replacement; replacement clears omitted optional fields.
- For covered profile config documents, treat `internals config-drafts generate` output as authoritative for the profile lane, source kind, required credential/auth reference, and YAML shape.
- `--auth` selects a stored auth display-name override; it does not create or edit credentials.
- `--mail-transport` is required when declarative mailbox fields are present.
- `filesystem` mailbox defaults accept `--mail-root` and reject Stalwart URL flags.
- `stalwart` mailbox defaults accept Stalwart URL flags and reject `--mail-root`.
- `--gateway-mail-notifier-appendix-text` stores a future runtime mail-notifier appendix default; it does not enable notifier polling by itself.
- Do not mix `--prompt-overlay-text` and `--prompt-overlay-file`.
- Do not mix `--memo-seed-text`, `--memo-seed-file`, and `--memo-seed-dir`; use at most one source.
- Supplying a new memo-seed source on `profile set` replaces the stored seed. `--clear-memo-seed` cannot be combined with a new source.
- Let the project profile or later project launch own ordinary same-root per-agent mailbox bootstrap when the mailbox identity will be derived from the managed-agent name.

- Apply prompt policy and run mode independently. Include clear flags only for requested fields.

## Guardrails

- DO NOT enter credential discovery for project profile creation.
- DO NOT use `internals native-agent launch-dossiers set` for project profile edits.
- DO NOT remove and recreate a project profile for ordinary default edits.
- DO NOT treat profile creation as launching or mutating a live managed agent.
- DO NOT add raw Kimi `--auto` or `--yolo` launch flags to profiles; use prompt mode for managed automation.
- DO NOT preregister same-root ordinary per-agent mailbox addresses as the default precursor to mailbox-enabled project launch.
- DO NOT pass hidden full-model defaults such as model, env, mailbox, memo seed, gateway, or prompt overlay fields to `project.profile` config drafts.
