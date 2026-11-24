# Manage Recipe-Backed Project Launch Profiles

## Workflow

1. Confirm the caller selected a project-local profile backed by a recipe or preset. Resolve its project, profile name, and source recipe when creating it.
2. Select the required `list`, `get`, `add`, `set`, or `remove` action from **Command Shapes**. Use the launcher chosen by the parent.
3. If the request sets or clears a tmux selector, apply **Saved Tmux Server**.
4. Report the persisted profile and any launch defaults that changed. For a tmux edit, verify the saved `defaults.posture.tmux` through `get`.

If the task does not fit these steps, use the native planning tool to plan from this command, its constraints, and the user's request, then execute the plan.

## Command Shapes

Use the selected project overlay and explicit values for the operation:

```bash
houmao-mgr project agents launch-profiles list
houmao-mgr project agents launch-profiles get --name "$PROFILE"
houmao-mgr project agents launch-profiles add --name "$PROFILE" --recipe "$RECIPE"
houmao-mgr project agents launch-profiles set --name "$PROFILE" --tmux-server houmao-default
houmao-mgr project agents launch-profiles remove --name "$PROFILE"
```

Use `profiles()` for a specialist-backed project profile, the lane accepted by `project agents launch --profile`. Use `launch-dossiers()` only for an explicitly selected native launch dossier.

## Saved Tmux Server

See [Tmux Server Choices](../../references/common/tmux-server.md) for the four modes. Use `--tmux-server socket --tmux-socket-path "$OWNER_SOCKET"` to store an existing absolute socket path in the execution owner's context. On `set`, omission preserves the selector, a new mode replaces it, and `--clear-tmux-server` restores the launch-time fallback.

## Guardrails

- DO NOT run the native launch-dossier command family to edit a recipe-backed project profile.
- DO NOT assume that saving a profile starts a tmux server or changes an existing agent's recorded socket.
- DO NOT use same-name replacement for a routine patch.
