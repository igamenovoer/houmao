## Why

`houmao-utils-workspace-mgr` currently treats `.pixi` as the only default local-state symlink candidate for agent worktrees. Real in-repo workspaces often depend on other local-only generated data, caches, model assets, or support directories that Git does not carry into each private worktree, so the current default can create structurally correct worktrees that are not runnable.

## What Changes

- Expand the default in-repo local-state symlink policy from `.pixi` only to:
  - every reachable `.pixi/` directory, at any depth, when the source subtree is local-only and not reached through a skipped hidden parent;
  - every explicit local-only path whose basename does not start with `.`, including nested local-only files and directories discovered under traversable source directories.
- Keep hidden local-state paths denied by default, including `.claude`, `.codex`, `.gemini`, `.aider`, `.cursor`, `.continue`, `.windsurf`, `.kiro`, `.env`, `.github`, and arbitrary hidden local directories or files.
- Define traversal rules: do not follow symlinked directories, do not descend into hidden local-only directories, and do not treat `.hidden-parent/.pixi/` as linkable because the hidden parent skip takes precedence.
- Define recursive tracked-content safety: a candidate is skipped when Git tracks any file under that source subtree or when the destination would replace tracked content in the agent worktree.
- Require plan and `workspace.md` output to record linked and skipped local-state paths with reasons.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-utils-workspace-mgr-skill`: Update the workspace-manager local-state symlink requirements for in-repo workspaces so default candidates include reachable `.pixi/` directories and explicit local-only non-hidden paths, while preserving hidden-path safety and recursive tracked-content conflict checks.

## Impact

- Packaged system skill asset:
  - `src/houmao/agents/assets/system_skills/houmao-utils-workspace-mgr/SKILL.md`
  - potentially `src/houmao/agents/assets/system_skills/houmao-utils-workspace-mgr/subskills/in-repo-workspace.md`
- OpenSpec requirement:
  - `openspec/specs/houmao-utils-workspace-mgr-skill/spec.md`
- Tests guarding packaged skill wording and asset shape:
  - `tests/unit/agents/test_system_skills.py`
- No new runtime dependency or public API is expected. This change updates the supported workspace-manager skill behavior and its documented contract.
