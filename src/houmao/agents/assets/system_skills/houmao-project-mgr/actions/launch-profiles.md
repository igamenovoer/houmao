# Manage Explicit Launch Profiles

Use this action only when the user wants to manage explicit recipe-backed launch profiles through `project agents launch-profiles ...`.

## Workflow

1. Determine whether the user wants to `list`, `get`, `add`, `set`, or `remove` one explicit launch profile.
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
<chosen houmao-mgr launcher> project agents launch-profiles set --name <profile> ...
<chosen houmao-mgr launcher> project agents launch-profiles remove --name <profile>
```

## Boundary Notes

- This is the explicit recipe-backed birth-time lane, not auth-bundle CRUD and not easy-profile authoring.
- `--auth` and `--clear-auth` here change the stored launch-profile override, not the underlying auth bundle contents.
- The shared conceptual model for easy profiles versus explicit launch profiles lives in `docs/getting-started/launch-profiles.md`.

## Guardrails

- Do not route `project easy profile ...` through this action.
- Do not treat launch-profile `--auth` changes as work for `houmao-credential-mgr`.
- Do not route low-level recipe editing through this action; that belongs to `houmao-agent-definition`.
- Do not invent launch-profile names, recipe names, or field overrides that the user did not provide.
