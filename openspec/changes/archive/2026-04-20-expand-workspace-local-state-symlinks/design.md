## Context

`houmao-utils-workspace-mgr` is a packaged utility skill that guides planning and execution of multi-agent workspaces. For in-repo workspaces, the parent checkout is the shared visibility surface while each agent receives a private Git worktree under `houmao-ws/<agent>/repo`.

The current local-state policy is intentionally conservative: it forbids AI-tool dot directories by default and only names `.pixi` as a default allowed local-state symlink candidate. Issue #21 shows that this is too narrow for repositories whose runnable local environment also depends on non-dot generated data, cache roots, model assets, or support directories that are intentionally not tracked by Git.

The feature remains a skill/spec behavior update. There is no current Python workspace execution engine to modify; the supported behavior is carried by the packaged skill text, the in-repo flavor page, the OpenSpec contract, and tests that guard packaged skill assets.

## Goals / Non-Goals

**Goals:**

- Expand in-repo workspace-manager defaults so agents receive symlinks for local-only runnable state that Git will not populate in their private worktrees.
- Preserve `.pixi/` as a special default symlink candidate at reachable depths.
- Preserve hidden-path safety: dot-prefixed local state stays skipped by default except reachable `.pixi/`.
- Define deterministic traversal precedence:
  - do not follow symlinked directories;
  - do not descend into skipped hidden local-only directories;
  - hidden parent skip takes precedence over nested `.pixi/` discovery.
- Define recursive tracked-content checks so any candidate subtree containing tracked files is skipped.
- Require plan and `workspace.md` output to report linked and skipped local-state decisions with reasons.

**Non-Goals:**

- Add a new workspace execution engine or CLI automation layer.
- Change out-of-repo workspace defaults except where shared top-level local-state policy wording naturally applies.
- Symlink AI tool homes, credential directories, provider homes, or arbitrary dot-prefixed local state by default.
- Replace Git-tracked content in an agent worktree.
- Follow symlinked directories while discovering candidates.

## Decisions

1. Treat `.pixi/` as a special default-allow candidate, but only when reachable.

   `.pixi/` remains useful repo-local environment state and should stay default-symlinked. The candidate can appear at the repository root or under traversable non-hidden directories. However, traversal does not enter hidden local-only directories, so `.hidden-parent/.pixi/` is not linked. This keeps `.pixi` useful without weakening the hidden-subtree safety boundary.

   Alternative considered: link every `.pixi/` regardless of hidden ancestors. Rejected because it requires descending into hidden local-state subtrees such as `.codex/` or `.claude/`, which undermines the skip rule.

2. Discover local-only paths recursively under traversable directories.

   The workspace manager should not only inspect top-level entries. If a tracked or otherwise traversable source directory contains local-only generated children such as `src/generated/` or `packages/api/model-cache/`, those children should be candidates. The symlink target should preserve the same relative path inside each agent worktree.

   Alternative considered: symlink only top-level local-only non-dot entries. Rejected because many repositories place generated support state under tracked source trees.

3. Use hidden basename as a default-deny rule.

   A local-only path whose basename starts with `.` is skipped by default unless the basename is exactly `.pixi` and the path is reachable. This covers `.env`, `.github`, `.cache`, `.claude`, `.codex`, `.gemini`, and arbitrary hidden local state. The rule applies at every depth.

   Alternative considered: enumerate only known AI-tool directories. Rejected because unknown dot directories are also more likely to hold machine-specific, credential, trust, or tool state.

4. Treat tracked-content detection as recursive.

   Git tracks files rather than directories, so a directory candidate must be skipped if any tracked file exists below it. For example, `fixtures/` is not linkable if `fixtures/input.json` is tracked, even when `fixtures/local-cache.bin` is local-only. The plan should continue to discover deeper local-only non-hidden children under traversable directories rather than replacing tracked subtrees wholesale.

   Alternative considered: only check whether the directory path itself is tracked. Rejected because it would allow a symlink to shadow tracked descendants in the worktree.

5. Keep the policy observable in plan output and `workspace.md`.

   Operators need to understand why local state did or did not appear in agent worktrees. Every linked candidate and meaningful skip should include the source relative path and reason, such as `linked: local-only non-hidden`, `linked: .pixi special case`, `skipped: hidden local state`, `skipped: source subtree contains tracked content`, `skipped: symlinked directory not followed`, or `skipped: destination would replace tracked content`.

   Alternative considered: report only linked paths. Rejected because silent skips make workspace failures hard to debug.

## Risks / Trade-offs

- [Risk] A broad recursive scan could be expensive in large repositories. -> Mitigation: rely on Git status/listing commands where possible and do not follow symlinked directories.
- [Risk] Symlinking more local state can expose large caches into every agent worktree. -> Mitigation: keep the policy restricted to local-only paths and make all decisions visible in the plan and `workspace.md`.
- [Risk] A non-hidden local-only path might still contain sensitive data. -> Mitigation: preserve hidden-path denial, document the policy, and keep explicit user overrides available for special cases.
- [Risk] Hidden parent precedence may surprise users with `.hidden-parent/.pixi/`. -> Mitigation: state the precedence explicitly in the skill and spec.
- [Risk] Recursive tracked-content checks can skip a broad directory the user expected to link. -> Mitigation: require skip reasons and allow narrower local-only child paths to be discovered under traversable directories.
