---
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Memo Seeds

Use this page only when the user opts in to launch-profile memo seed generation.

Create a Markdown memo seed per agent that combines original memo seed text with workspace rules.

Memo seed content should include:

- launch cwd
- branch names for superproject and submodules
- writable knowledge and bookkeeping paths
- shared knowledge paths and ownership
- source write targets
- per-run owner-state paths and ownership
- local-state link policy
- submodule commit and push rules
- integration rule: avoid submodule structure changes; expect cherry-pick or path-limited merge

For `in-repo` memo seeds, state that the agent launches from `<repo-root>` for shared visibility, writes source changes inside `<repo-root>/houmao-ws/<task-name>/<agent-name>/repo`, uses `<repo-root>/houmao-ws/<task-name>/shared-kb` for untracked cross-run task knowledge when assigned, uses `<repo-root>/houmao-ws/<task-name>/owner-states/<subdir>/...` for untracked per-run task-owner bookkeeping when assigned, may write its own `<repo-root>/houmao-ws/<task-name>/<agent-name>/states` bookkeeping path, and treats sibling bookkeeping directories, sibling task worktrees, parent-checkout source, task-local `workspace.md`, and repo-level `workspaces.md` as read-only by default.

Preserve original memo seed text verbatim in a clearly labeled section, then append workspace rules. Update the launch profile to use the generated memo seed file only after writing it.

Use `<public-entrypoint>->houmao-shared-routines->memory-mgr` for direct live-agent memo edits; this skill only prepares launch-profile memo seeds before launch.
