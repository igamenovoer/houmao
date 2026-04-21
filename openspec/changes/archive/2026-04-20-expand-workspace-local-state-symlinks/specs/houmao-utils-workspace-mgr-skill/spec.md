## MODIFIED Requirements

### Requirement: Workspace-manager skill avoids unsafe AI-tool local-state symlinks
The workspace-manager skill SHALL evaluate local-state symlink candidates explicitly instead of blindly applying generic worktree symlink defaults.

For Houmao agent workspaces, the skill SHALL NOT symlink AI tool state directories by default, including `.claude`, `.codex`, `.gemini`, `.aider`, `.cursor`, `.continue`, `.windsurf`, and `.kiro`.

For in-repo Houmao agent workspaces, the skill SHALL default to discovering local-state symlink candidates recursively from the parent checkout without following symlinked directories.

The skill SHALL treat a reachable directory whose basename is `.pixi` as a default local-state symlink candidate when the source subtree contains no Git-tracked files and the destination would not replace tracked content in the worktree.

The skill SHALL treat local-only paths whose basename does not start with `.` as default local-state symlink candidates when the source subtree contains no Git-tracked files and the destination would not replace tracked content in the worktree.

The skill SHALL skip dot-prefixed local-only paths by default, except for reachable `.pixi` directories.

The skill SHALL NOT descend into skipped hidden local-only directories while discovering candidates. Therefore, a nested `.pixi` directory under a skipped hidden local-only parent SHALL NOT be linked by default.

The skill SHALL skip any candidate whose source is missing, whose source subtree contains Git-tracked files, whose source is discovered only by following a symlinked directory, or whose destination would replace tracked content in the worktree.

Every linked or skipped local-state path SHALL be recorded in the plan and in `workspace.md` when execution occurs.

#### Scenario: AI tool homes are skipped by default
- **WHEN** a source repository contains `.claude`, `.codex`, or `.gemini`
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill does not symlink those directories into agent worktrees
- **AND THEN** it records the skip decision and reason in the workspace plan

#### Scenario: In-repo workspace links reachable pixi and non-hidden local-only paths
- **WHEN** a parent checkout contains reachable local-only paths `.pixi/`, `data-local/`, `src/generated/`, and `packages/api/model-cache/`
- **AND WHEN** those source subtrees contain no Git-tracked files
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill plans local-state symlinks for `.pixi/`, `data-local/`, `src/generated/`, and `packages/api/model-cache/` into each agent worktree at the same relative paths
- **AND THEN** it records each link decision in the workspace plan and `workspace.md`

#### Scenario: Hidden local-only paths are skipped except reachable pixi
- **WHEN** a parent checkout contains local-only paths `.env`, `.cache/`, `src/.cache/`, `.github/`, and `tools/.pixi/`
- **AND WHEN** `tools/` is traversable without following a symlinked directory
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill skips `.env`, `.cache/`, `src/.cache/`, and `.github/`
- **AND THEN** it plans a local-state symlink for `tools/.pixi/` when that source subtree contains no Git-tracked files and the destination would not replace tracked content
- **AND THEN** it records the skip and link reasons in the workspace plan

#### Scenario: Hidden parent skip takes precedence over nested pixi
- **WHEN** a parent checkout contains local-only path `.hidden-parent/.pixi/`
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill skips `.hidden-parent/` as hidden local state
- **AND THEN** it does not descend into `.hidden-parent/`
- **AND THEN** it does not plan a symlink for `.hidden-parent/.pixi/`

#### Scenario: Recursive tracked content blocks a directory candidate
- **WHEN** a parent checkout contains directory `fixtures/`
- **AND WHEN** Git tracks `fixtures/input.json`
- **AND WHEN** `fixtures/` also contains local-only path `fixtures/local-cache.bin`
- **THEN** the workspace-manager skill does not plan a symlink for `fixtures/` as a whole
- **AND THEN** it records that `fixtures/` is skipped because the source subtree contains tracked content
- **AND THEN** it may still consider narrower local-only non-hidden descendants according to the same candidate rules

#### Scenario: Symlinked directories are not followed during discovery
- **WHEN** a parent checkout contains a symlinked directory `external-state/`
- **AND WHEN** the symlink target contains local-only non-hidden paths or `.pixi/`
- **AND WHEN** the user has not explicitly overridden the local-state symlink policy
- **THEN** the workspace-manager skill does not follow `external-state/` during candidate discovery
- **AND THEN** it records the skip reason in the workspace plan
