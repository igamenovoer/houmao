# Launch Dossiers

Use this subskill when the user explicitly wants native launch dossiers, recipe-backed native launch defaults, or the exact `internals native-agent launch-dossiers ...` surface.

Launch dossiers are low-level native-agent launch material. The maintained CLI surface is `houmao-mgr internals native-agent launch-dossiers ...`.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Read [../common/profile-lanes.md](../common/profile-lanes.md).
- Read [../common/credential-routing.md](../common/credential-routing.md) when auth overrides are involved.
- Confirm the user explicitly wants provider-aligned native launch material rather than an ordinary project profile.

## Workflow

1. Determine the action: `list`, `get`, `add`, `set`, `replace`, or `remove`.
2. Recover required launch-dossier inputs from the prompt and explicit recent context.
3. Ask for any missing required inputs before running a command.
4. Use the chosen `houmao-mgr` launcher.
5. Run the matching launch-dossier command.
6. Report the returned launch-dossier data and any defaults that affect later launch.

## Command Shapes

```text
<chosen houmao-mgr launcher> internals native-agent launch-dossiers list
<chosen houmao-mgr launcher> internals native-agent launch-dossiers get --name <name>
<chosen houmao-mgr launcher> internals native-agent launch-dossiers remove --name <name>
```

For `add`, same-name replacement, and launch-dossier config-document preparation, use the CLI-owned config draft before running the maintained command:

```text
<chosen houmao-mgr launcher> internals config-drafts generate --id internals.native-agent.launch-dossier --intent '<json>'
```

The `internals.native-agent.launch-dossier` config draft is intentionally minimal. Its intent fields are only `name`, `recipe`, and `credential`. For model, env, mailbox, launch posture, managed header, prompt overlay, notifier appendix, memo seed, relaunch policy, or other stored defaults, use the maintained `internals native-agent launch-dossiers add|set` fields directly instead of adding them to the draft intent.

## Add And Set Fields

- `--agent-name`
- `--agent-id`
- `--workdir`
- `--auth`
- `--model`
- `--reasoning-level`
- `--prompt-mode unattended|as_is`
- repeatable `--env-set NAME=value`
- launch posture: `--headless`, `--no-gateway`, `--gateway-port`

## Set Clear Fields

- `--clear-auth`
- `--clear-workdir`
- `--clear-model`
- `--clear-reasoning-level`
- `--clear-prompt-mode`

## Notes

- The skill subcommand is `launch-dossiers`; the CLI command family is `internals native-agent launch-dossiers ...`.
- `launch-dossiers set` patches without dropping unspecified defaults.
- `launch-dossiers add --yes` is only for intended same-name replacement; omitted optional fields are cleared.
- For covered launch-dossier config documents, treat `internals config-drafts generate` output as authoritative for source kind, required credential/auth reference, and YAML shape.
- `--auth` and `--clear-auth` change the launch-dossier auth override by display name; they do not mutate credential bundle contents.

## Guardrails

- Do not route `project profile ...` through this subskill.
- Do not route loosely stated profile requests here; use `profiles` unless the user explicitly asks for native launch dossiers.
- Do not remove and recreate a launch dossier for ordinary edits.
- Do not treat launch-dossier `--auth` changes as credential CRUD.
- Do not route low-level recipe editing through this subskill.
- Do not store `--headless` by default for TUI-capable tools.
- Do not add `--prompt-mode`, `--headless`, or clear flags unless the user explicitly supplied those fields.
- Do not invent launch-dossier names, recipe names, or field overrides.
