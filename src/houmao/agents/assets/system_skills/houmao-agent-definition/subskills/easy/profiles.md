# Easy Profiles

Use this subskill when the user wants to create, inspect, update, list, replace, or remove one specialist-backed easy profile through `project easy profile ...`.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Read [../common/profile-lanes.md](../common/profile-lanes.md).
- Read [../common/credential-routing.md](../common/credential-routing.md) when auth overrides are involved.
- Confirm the profile lane is specialist-backed easy profile, not explicit recipe-backed launch profile.

## Actions

- List profiles: no name required.
- Get profile: require `--name`.
- Create profile: require `--name` and `--specialist`.
- Set profile: require `--name` and at least one update or clear field.
- Replace profile: use `create --yes` only when the user intends same-name replacement.
- Remove profile: require `--name`.

## Command Shapes

```text
<chosen houmao-mgr launcher> project easy profile list
<chosen houmao-mgr launcher> project easy profile get --name <name>
<chosen houmao-mgr launcher> project easy profile create --name <profile> --specialist <specialist> ...
<chosen houmao-mgr launcher> project easy profile create --name <profile> --specialist <specialist> --yes ...
<chosen houmao-mgr launcher> project easy profile set --name <profile> ...
<chosen houmao-mgr launcher> project easy profile remove --name <profile>
```

## Stored Defaults

Easy profiles may store:

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

When the user does not specify headless or TUI posture, omit `--headless`. An easy profile without stored headless posture remains TUI/local-interactive preferred on later launch when the selected tool supports it.

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

- Use `project easy profile set` for ordinary edits.
- Use `project easy profile create --yes` only for intended same-name replacement; replacement clears omitted optional fields.
- `--auth` selects a stored auth display-name override; it does not create or edit credentials.
- `--mail-transport` is required when declarative mailbox fields are present.
- `filesystem` mailbox defaults accept `--mail-root` and reject Stalwart URL flags.
- `stalwart` mailbox defaults accept Stalwart URL flags and reject `--mail-root`.
- `--gateway-mail-notifier-appendix-text` stores a future runtime mail-notifier appendix default; it does not enable notifier polling by itself.
- Do not mix `--prompt-overlay-text` and `--prompt-overlay-file`.
- Do not mix `--memo-seed-text`, `--memo-seed-file`, and `--memo-seed-dir`; use at most one source.
- Supplying a new memo-seed source on `profile set` replaces the stored seed. `--clear-memo-seed` cannot be combined with a new source.
- Let the easy profile or later easy launch own ordinary same-root per-agent mailbox bootstrap when the mailbox identity will be derived from the managed-agent name.

## Guardrails

- Do not enter credential discovery for easy-profile creation.
- Do not use `project agents launch-profiles set` for easy-profile edits.
- Do not remove and recreate an easy profile for ordinary default edits.
- Do not treat profile creation as launching or mutating a live easy instance.
- Do not store `--headless` by default for TUI-capable tools.
- Do not preregister same-root ordinary per-agent mailbox addresses as the default precursor to mailbox-enabled easy launch.
