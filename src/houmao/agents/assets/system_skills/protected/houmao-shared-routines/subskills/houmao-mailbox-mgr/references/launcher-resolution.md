# Launcher Resolution

Use this reference when the mailbox-admin task needs the exact supported `houmao-mgr` launcher for the current workspace.

Resolve the launcher in this order:

1. run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
2. if that lookup fails, use `uv tool run --from houmao houmao-mgr`
3. only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
4. if the user explicitly asks for a specific launcher, follow that request instead of the default order

Notes:

- Prefer the PATH-resolved `houmao-mgr` command first; it is the ordinary launcher when available.
- The uv-managed fallback matches Houmao's documented official installation path.
- Only probe development-project hints after the PATH lookup and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.
- Reuse one chosen launcher for the entire mailbox-admin turn instead of mixing launchers across commands.
