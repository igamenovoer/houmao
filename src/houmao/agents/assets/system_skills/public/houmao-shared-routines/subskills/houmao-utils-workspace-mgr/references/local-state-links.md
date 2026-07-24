# Local-State Links

Do not blindly reuse generic worktree symlink defaults.

## AI Tool State

Never symlink these AI tool directories into Houmao agent worktrees by default:

```text
.claude
.codex
.gemini
.aider
.cursor
.continue
.windsurf
.kiro
```

These can contain provider homes, credentials, trust state, local agent state, or project config that can override Houmao launch-owned settings.

## Discovery

For in-repo workspaces, discover local-state link candidates recursively from the parent checkout. Do not follow symlinked directories while discovering candidates.

Default allowed candidates:

- reachable `.pixi/` directories, at any depth
- explicitly local-only files or directories whose basename does not start with `.`

Hidden local-state paths are skipped by default at every depth, including `.env`, `.github`, `.claude`, `.codex`, `.gemini`, `.aider`, `.cursor`, `.continue`, `.windsurf`, `.kiro`, and arbitrary dot-prefixed files or directories. `.pixi/` is the only default dot-prefixed exception, and it must be reachable without entering a skipped hidden parent. For example, `tools/.pixi/` can be linked when `tools/` is traversable, but `.hidden-parent/.pixi/` is skipped because `.hidden-parent/` takes precedence.

Python virtual environments such as `.venv/` are validation signals, not default link targets. Link them only when the operator, plan, or project policy explicitly marks that environment as local-only and required for the prepared worktree.

## Link Rules

For every candidate:

- link only if the source exists and is explicitly local-only
- skip if Git tracks any files under the source subtree
- skip if the source is discovered only by following a symlinked directory
- do not replace tracked content in the worktree
- preserve relative paths for linked local-only state
- record linked and skipped paths in `workspace.md`

## Completeness

Creation must not leave necessary project state unlinked. If a known project tool requires a local-only directory or file, record it as required in the plan and create report. Validation must check required links and report missing paths.
