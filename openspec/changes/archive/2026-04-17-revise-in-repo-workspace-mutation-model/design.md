## Context

`houmao-utils-workspace-mgr` currently describes the in-repo workspace flavor as if each launched agent should start inside its private worktree at `<repo-root>/houmao-ws/<agent-name>/repo`. That gives each agent a safe source mutation surface, but it also hides sibling agent workspaces from the default view and can make Houmao project-aware resolution depend on the nested worktree instead of the parent repository.

The intended in-repo collaboration model is different: the parent repository root is the shared visibility surface, while each agent's private worktree remains the safe source and shared-KB mutation surface. Agent-owned parent-checkout KB directories provide a direct note-sharing surface that sibling agents can read immediately without writing into one another's files.

## Goals / Non-Goals

**Goals:**

- Make `<repo-root>` the default launch cwd for in-repo workspaces.
- Preserve per-agent Git worktrees as the only default write targets for source changes and shared-KB changes intended to merge through Git.
- Allow each agent to write its own parent-checkout KB path while treating sibling KB paths and sibling worktrees as read-only by default.
- Ensure generated plans, `workspace.md`, and optional memo seeds communicate the read/write ownership contract clearly enough for launched agents and operators.

**Non-Goals:**

- Redesign the out-of-repo workspace flavor.
- Add a new workspace execution engine or automate Git merge behavior.
- Change Houmao project-aware overlay resolution.
- Prevent every possible accidental write in the parent checkout with filesystem permissions; this change is an operating-contract and documentation update.

## Decisions

1. Use repo root as the in-repo launch cwd.

   The launch cwd should optimize for project-aware Houmao operations and shared visibility. Starting agents at `<repo-root>` lets them inspect the parent checkout, `workspace.md`, sibling KB directories, and sibling private worktrees from one stable location. The private worktree is still created, but it becomes a named write target instead of the process cwd.

   Alternative considered: keep cwd inside the private worktree and add symlinks or relative paths to sibling workspaces. That preserves source-write safety by default, but it makes cross-agent visibility more indirect and can make project-aware discovery resolve against the nested worktree.

2. Treat mutation authority as path-scoped.

   The in-repo flavor should describe a path ownership table: parent source is read-only by default, own worktree is writable for source and branch-local workspace changes, own parent KB is writable for agent-owned notes, sibling KB and sibling worktrees are read-only by default, and `workspace.md` remains operator/workspace-manager owned.

   Alternative considered: make the parent checkout shared KB writable. That would provide fast shared edits, but it creates unmediated concurrent modification risk. Shared-KB changes that need Git conflict handling should happen in the agent's private worktree copy.

3. Keep agent-specific KB in the parent checkout writable by its owner.

   Agent-specific KB is the lightweight direct communication surface. Each agent owns `<repo-root>/houmao-ws/<agent-name>/kb/**`; peers can read it directly but should not write it. These files are not isolated by per-agent branches, so implementation guidance should mention narrow pathspec commits or operator curation when committing parent-checkout KB updates.

   Alternative considered: require agent KB writes inside the private worktree only. That would make every knowledge update merge through Git, but it would remove the immediate shared visibility that motivates the in-repo layout.

4. Carry the ownership contract into plans, `workspace.md`, and memo seeds.

   The skill should not rely on one paragraph in the subskill page. Plans must show the launch cwd and read/write targets; `workspace.md` must preserve the operating contract after execution; memo seeds should include the same rules when the user opts in, because memo seeds are the most durable way to keep launched agents aligned.

## Risks / Trade-offs

- Parent-checkout source files are visible and near the cwd, so an agent may edit the wrong tree → Mitigate by making source write targets explicit in plans, `workspace.md`, and memo seeds, and by warning that parent source is read-only by default.
- Agent-owned parent KB writes are not branch-isolated → Mitigate by documenting per-agent ownership and recommending operator-curated or narrow pathspec commits for those paths.
- Agents may misinterpret sibling worktrees as shared scratch space → Mitigate by documenting sibling worktrees as read-only by default and reserving cross-agent source integration for Git merge, cherry-pick, or operator review.
- Out-of-repo wording could accidentally inherit in-repo cwd rules → Mitigate by keeping the cwd/write-target rule in the in-repo subskill and using top-level launch-profile text that defers to the selected flavor.
