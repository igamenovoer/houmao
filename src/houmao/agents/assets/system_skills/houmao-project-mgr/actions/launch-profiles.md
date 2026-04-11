# Manage Explicit Launch Profiles

Use this action only when the user wants to manage explicit recipe-backed launch profiles through `project agents launch-profiles ...`.

## Workflow

1. Determine whether the user wants to `list`, `get`, `add`, `set`, `replace`, or `remove` one explicit launch profile.
2. Recover required launch-profile inputs from the current prompt first and recent chat context second when they were stated explicitly.
3. If the action or the required inputs are still ambiguous, ask before proceeding.
4. Use the `houmao-mgr` launcher already chosen by the top-level skill.
5. Run the matching launch-profile command.
6. Report the resulting launch-profile data from the command output.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project agents launch-profiles list
<chosen houmao-mgr launcher> project agents launch-profiles get --name <profile>
<chosen houmao-mgr launcher> project agents launch-profiles add --name <profile> --recipe <recipe> ...
<chosen houmao-mgr launcher> project agents launch-profiles add --name <profile> --recipe <recipe> --yes ...
<chosen houmao-mgr launcher> project agents launch-profiles set --name <profile> ...
<chosen houmao-mgr launcher> project agents launch-profiles remove --name <profile>
```

## Boundary Notes

- This is the explicit recipe-backed birth-time lane, not auth-bundle CRUD and not easy-profile authoring.
- Use `launch-profiles set` for ordinary patch edits to existing explicit launch profiles.
- `launch-profiles set` accepts the same default override options as `add`, plus clear flags such as `--clear-auth`, `--clear-env`, `--clear-mailbox`, and `--clear-prompt-overlay`.
- Managed prompt-header section policy is stored with repeatable `--managed-header-section SECTION=enabled|disabled`; patch edits can remove one entry with `--clear-managed-header-section SECTION` or all entries with `--clear-managed-header-sections`.
- Use `launch-profiles add --yes` only when the user intends same-name replacement; replacement is same-lane only and clears omitted optional fields.
- `--auth` and `--clear-auth` here change the stored launch-profile auth override, not the underlying auth bundle contents. The CLI accepts auth display names, but the stored relationship resolves through auth-profile identity so later auth rename stays valid.
- The shared conceptual model for easy profiles versus explicit launch profiles lives in `docs/getting-started/launch-profiles.md`.

## Guardrails

- Do not route `project easy profile ...` through this action.
- Do not remove and recreate an explicit launch profile for ordinary edits; use `launch-profiles set` or `launch-profiles add --yes` when replacement is intended.
- Do not treat launch-profile `--auth` changes as work for `houmao-credential-mgr`.
- Do not route low-level recipe editing through this action; that belongs to `houmao-agent-definition`.
- Do not invent launch-profile names, recipe names, or field overrides that the user did not provide.
