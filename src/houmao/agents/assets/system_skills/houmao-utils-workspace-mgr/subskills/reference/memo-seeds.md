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

Use `houmao-memory-mgr` for direct live-agent memo edits; this skill only prepares launch-profile memo seeds before launch.
