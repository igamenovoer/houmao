# Project Profiles

Use this subskill when the user wants to create, inspect, update, list, replace, or remove one specialist-backed project profile through `project profile ...`.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Read [../common/profile-lanes.md](../common/profile-lanes.md).
- Read [../common/credential-routing.md](../common/credential-routing.md) when auth overrides are involved.
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
<chosen houmao-mgr launcher> internals config-drafts generate --id project.profile --intent '<json>'
```

The `project.profile` config draft is intentionally minimal. Its intent fields are only `name`, `specialist`, and `credential`. The draft fixes the project profile lane and specialist source kind, then records the credential as the profile auth reference. For model, env, mailbox, launch posture, managed header, prompt overlay, notifier appendix, memo seed, or other stored defaults, use the maintained `project profile create|set` fields directly instead of adding them to the draft intent.

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
- launch posture: `--headless`, `--no-gateway`, `--gateway-port`
- managed prompt header: `--managed-header`, `--no-managed-header`, repeatable `--managed-header-section SECTION=enabled|disabled`
- prompt overlay: `--prompt-overlay-mode append|replace`, `--prompt-overlay-text`, `--prompt-overlay-file`
- gateway mail-notifier default: `--gateway-mail-notifier-appendix-text`
- memo seed: `--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`

## Default Launch Posture

When the user does not specify headless or TUI posture, omit `--headless`. An project profile without stored headless posture remains TUI/local-interactive preferred on later launch when the selected tool supports it.

Only persist `--headless` when the user explicitly asks for headless execution or the selected tool/lane is known to require headless. Do not infer headless from `--prompt-mode unattended`, mailbox defaults, gateway defaults, model defaults, or automation-oriented wording.

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
- `--clear-headless`
- `--clear-managed-header`
- `--clear-managed-header-section SECTION`
- `--clear-managed-header-sections`
- `--clear-prompt-overlay`
- `--clear-gateway-mail-notifier-appendix`
- `--clear-memo-seed`

## Rules

- Use `project profile set` for ordinary edits.
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

## Guardrails

- Do not enter credential discovery for project profile creation.
- Do not use `internals native-agent launch-dossiers set` for project profile edits.
- Do not remove and recreate a project profile for ordinary default edits.
- Do not treat profile creation as launching or mutating a live managed agent.
- Do not store `--headless` by default for TUI-capable tools.
- Do not add `--prompt-mode`, `--headless`, or clear flags unless the user explicitly supplied those fields.
- Do not preregister same-root ordinary per-agent mailbox addresses as the default precursor to mailbox-enabled project launch.
- Do not pass hidden full-model defaults such as model, env, mailbox, memo seed, gateway, or prompt overlay fields to `project.profile` config drafts.
