## Why

The current in-repo workspace-manager guidance treats each agent's private worktree as the launch cwd, which prevents agents from naturally seeing sibling agent workspaces and can shift Houmao project-aware discovery away from the parent repository. In-repo workspaces should instead make the parent repo root the shared visibility surface while keeping mutations confined to safe per-agent paths.

## What Changes

- Revise the in-repo workspace flavor so all agents default to launching with cwd at `<repo-root>`.
- Document the in-repo workspace as a shared-visibility, private-mutation model: agents may inspect the parent checkout and sibling workspace files, but source and shared-KB changes must be made in the agent's private Git worktree.
- Clarify that each agent's own parent-checkout KB directory is writable for agent-owned notes, while other agents' KB directories and worktrees are read-only by default.
- Update workspace plans, `workspace.md`, and optional memo-seed rules to include explicit read/write ownership rules for parent source, private worktrees, shared KB, agent KB, sibling KB, and sibling worktrees.
- Adjust launch-profile guidance so flavor-specific planned cwd values are respected; for in-repo workspaces that planned cwd is `<repo-root>`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-utils-workspace-mgr-skill`: Revise in-repo workspace requirements to separate shared cwd visibility from safe mutation targets.

## Impact

- Affected packaged skill assets: `src/houmao/agents/assets/system_skills/houmao-utils-workspace-mgr/SKILL.md` and `src/houmao/agents/assets/system_skills/houmao-utils-workspace-mgr/subskills/in-repo-workspace.md`.
- Affected requirements: `openspec/specs/houmao-utils-workspace-mgr-skill/spec.md`.
- Tests should cover the packaged asset wording or projection output sufficiently to prevent reverting the in-repo cwd/write-target contract.
