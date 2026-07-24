# Launcher Resolution

Use this page before any subskill that runs `houmao-mgr`.

## Default Order

1. Run `command -v houmao-mgr`.
2. If found, use that `houmao-mgr` for the whole turn.
3. If not found, use `uv tool run --from houmao houmao-mgr`.
4. If that does not satisfy the turn, choose the matching development launcher:
   - `pixi run houmao-mgr`
   - repo-local `.venv/bin/houmao-mgr`
   - project-local `uv run houmao-mgr`
5. If the user explicitly requests one launcher, use it instead of the default order.

## Rules

- Reuse one chosen launcher for all commands in the same task.
- Do not probe Pixi, `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user asked for them.
- Do not use `houmao-cli`.
- Report the command shape you ran when returning results.
