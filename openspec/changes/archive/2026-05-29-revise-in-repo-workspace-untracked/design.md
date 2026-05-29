## Context

`houmao-utils-workspace-mgr` currently describes in-repo workspaces as task-scoped under `<repo-root>/houmao-ws/<task-name>`, but parts of the contract still imply that shared workspace knowledge is a Git merge surface. The intended posture is now different: the workspace collection lives under the repository for convenience and visibility, but it is local runtime state and must remain untracked. Agents still need Git worktrees for source changes, so the design separates local coordination surfaces from Git-facing mutation surfaces.

The current repository is under active development and backward compatibility is not a priority. This change can update the system skill contract directly rather than preserving the old shared-KB merge semantics.

## Goals / Non-Goals

**Goals:**

- Make `<repo-root>/houmao-ws` the default untracked in-repo workspace collection directory.
- Keep task workspaces under `<repo-root>/houmao-ws/<task-name>` so multiple teams can coexist in the same repository.
- Define `<task-name>/shared-kb/` as untracked cross-run task knowledge.
- Define `<task-name>/owner-states/<subdir>/...` as untracked per-run task-owner bookkeeping.
- Keep per-agent private Git worktrees as the default source mutation surface.
- Update workspace maps, memo seed guidance, and loop-facing summaries to use the new local-state vocabulary.

**Non-Goals:**

- Do not make `houmao-ws` a standalone Git repository.
- Do not preserve the old model where shared-KB changes are intended to merge through Git.
- Do not prescribe a fixed hierarchy inside `shared-kb/`, `owner-states/<subdir>/`, or agent-local bookkeeping beyond the standard surfaces.
- Do not change out-of-repo workspace semantics except where shared wording must avoid implying that all workspace modes are tracked.

## Decisions

1. Default the in-repo workspace collection to `<repo-root>/houmao-ws` and require it to be untracked.

   The workspace collection remains easy to find from the repository root, but it is not part of the repository contract. Execution should ignore it by default through `.git/info/exclude` so creating a local workspace does not modify tracked `.gitignore` unless the user explicitly requests that.

   Alternative considered: move the collection outside the repository. That avoids ignore handling, but loses the simple "workspace beside the repo" ergonomics and makes launch/profile paths less obvious.

2. Make task workspaces the collision boundary.

   Each in-repo task workspace lives at `<repo-root>/houmao-ws/<task-name>`. The task root owns `workspace.md`, `shared-kb/`, `states/`, and per-agent directories. This keeps multiple teams with the same agent names from colliding as long as their task names differ.

   Alternative considered: keep a repo-level `shared-kb` and per-agent directories directly under `houmao-ws`. That makes cross-team collisions more likely and weakens the task-local operating contract.

3. Split task knowledge from run bookkeeping.

   `shared-kb/` is task-level knowledge that may persist across loop runs. `owner-states/<subdir>/...` is run-scoped task-owner bookkeeping. The workspace-manager records the chosen owner-state subdir when planning or executing a run but does not impose a universal subdirectory taxonomy.

   Alternative considered: put all bookkeeping under `shared-kb/`. That blurs durable task knowledge with run records and makes cleanup/reuse harder.

4. Keep Git-facing changes inside agent worktrees.

   Each agent receives a private Git worktree under its task-local agent directory. Source changes and submodule changes intended for Git belong there. Shared task knowledge and owner state remain untracked local files.

   Alternative considered: store shared-KB changes inside a worktree copy so they can merge through Git. That is the behavior being retired.

## Risks / Trade-offs

- Existing guidance or tests may expect `shared-kb` to be a Git merge surface → Update spec, packaged skill text, generated memo seed expectations, and tests together.
- Local `houmao-ws` contents are not durable through Git → Make `workspace.md` and loop-facing summaries explicit that `shared-kb` is local cross-run state, and operators must back it up or export it if they need durability outside the machine.
- `.git/info/exclude` is local-only and invisible to collaborators → Report ignore decisions in the plan and `workspace.md`, and allow an explicit tracked `.gitignore` update when the operator wants a repository-wide ignore rule.
- Per-run owner-state naming can drift between operators → Require plans and workspace maps to record the selected `owner-states/<subdir>` path without prescribing a single global naming scheme.
