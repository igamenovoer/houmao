# Explicit Recipe-Backed Launch Profiles

Use this subskill when the user wants to list, inspect, add, update, replace, or remove explicit recipe-backed launch profiles through `project agents launch-profiles ...`.

## Preconditions

- Read [../common/launcher.md](../common/launcher.md).
- Read [../common/missing-inputs.md](../common/missing-inputs.md).
- Read [../common/profile-lanes.md](../common/profile-lanes.md).
- Read [../common/credential-routing.md](../common/credential-routing.md) when auth overrides are involved.
- Confirm the profile lane is explicit recipe-backed, not specialist-backed easy profile.

## Workflow

1. Determine the action: `list`, `get`, `add`, `set`, `replace`, or `remove`.
2. Recover required launch-profile inputs from the prompt and explicit recent context.
3. Ask for any missing required inputs before running a command.
4. Use the chosen `houmao-mgr` launcher.
5. Run the matching launch-profile command.
6. Report the returned profile data and any defaults that affect later launch.

## Command Shapes

```text
<chosen houmao-mgr launcher> project agents launch-profiles list
<chosen houmao-mgr launcher> project agents launch-profiles get --name <profile>
<chosen houmao-mgr launcher> project agents launch-profiles add --name <profile> --recipe <recipe> ...
<chosen houmao-mgr launcher> project agents launch-profiles add --name <profile> --recipe <recipe> --yes ...
<chosen houmao-mgr launcher> project agents launch-profiles set --name <profile> ...
<chosen houmao-mgr launcher> project agents launch-profiles remove --name <profile>
```

## Add And Set Fields

- `--agent-name`
- `--agent-id`
- `--workdir`
- `--auth`
- `--model`
- `--reasoning-level`
- `--prompt-mode unattended|as_is`
- repeatable `--env-set NAME=value`
- mailbox defaults: `--mail-transport filesystem|stalwart`, `--mail-principal-id`, `--mail-address`, `--mail-root`, `--mail-base-url`, `--mail-jmap-url`, `--mail-management-url`
- launch posture: `--headless`, `--no-gateway`, `--gateway-port`
- relaunch chat-session defaults when supported by the current CLI
- managed prompt header: `--managed-header`, `--no-managed-header`, repeatable `--managed-header-section SECTION=enabled|disabled`
- prompt overlay: `--prompt-overlay-mode append|replace`, `--prompt-overlay-text`, `--prompt-overlay-file`
- gateway mail-notifier default: `--gateway-mail-notifier-appendix-text`
- memo seed: `--memo-seed-text`, `--memo-seed-file`, `--memo-seed-dir`

## Set Clear Fields

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
- `--clear-relaunch-chat-session`
- `--clear-managed-header`
- `--clear-managed-header-section SECTION`
- `--clear-managed-header-sections`
- `--clear-prompt-overlay`
- `--clear-gateway-mail-notifier-appendix`
- `--clear-memo-seed`

## Notes

- `launch-profiles set` patches without dropping unspecified defaults.
- `launch-profiles add --yes` is only for intended same-name replacement; omitted optional fields are cleared.
- `--auth` and `--clear-auth` change the profile auth override by display name; they do not mutate credential bundle contents.
- `--gateway-mail-notifier-appendix-text` stores a future runtime notifier prompt appendix default; launching from the profile seeds runtime notifier state but does not enable polling.
- Memo seeds replace only represented components. Text and file seeds touch only `houmao-memo.md`; directory seeds touch `houmao-memo.md` only when present and pages only when `pages/` is present.
- Use `--memo-seed-text ''` for an intentional empty memo seed. Use `--clear-memo-seed` only when removing stored seed configuration.

## Guardrails

- Do not route `project easy profile ...` through this subskill.
- Do not remove and recreate an explicit launch profile for ordinary edits.
- Do not treat launch-profile `--auth` changes as credential CRUD.
- Do not route low-level recipe editing through this subskill.
- Do not invent launch-profile names, recipe names, or field overrides.
