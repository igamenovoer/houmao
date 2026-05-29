## Context

`houmao-utils-workspace-mgr/SKILL.md` currently mixes operation routing, flavor layout rules, local-state symlink policy, submodule materialization, launch-profile handling, memo seed guidance, and workspace documentation rules in one long entrypoint. `houmao-agent-loop-pro` uses a more maintainable shape: a concise top-level router with operation lists and routed pages that hold detailed behavior.

The workspace-manager skill should follow that style while remaining independent of loop-specific concepts. Other skills may call it, but the workspace-manager contract should be about workspace preparation, validation, and summary production for any caller.

## Goals / Non-Goals

**Goals:**

- Make the workspace-manager top-level `SKILL.md` a concise router with structured operation and routing tables.
- Split `create` and `validate` into distinct operations.
- Keep `plan` as dry-run topology planning.
- Add `summarize` as a consumer-neutral prepared-workspace fact report.
- Move detailed behavior into operation, flavor, and reference pages.
- Validate that prepared worktrees can run project-scope commands and have required local state linked or materialized.
- Keep workspace-manager independent from `houmao-agent-loop-pro` and loop vocabulary.

**Non-Goals:**

- Do not change `houmao-agent-loop-pro` routing in this change.
- Do not introduce a Python implementation for workspace management unless existing tests or assets require it.
- Do not invent heavy project build commands; validation should use discovered safe probes, explicit operator commands, or documented project commands.
- Do not make validation create or repair workspace topology. It may run project tools that create normal cache/build outputs.

## Decisions

1. Use `create` as the standard mutating setup operation.

   `create` says what the operation does: create or update workspace topology. `execute` is less specific and currently absorbs both topology creation and readiness checking. If retained, `execute` should be documented only as a compatibility alias for `create`.

   Alternative considered: keep `execute` and add `validate`. That avoids renaming, but keeps an ambiguous operation name in the public skill contract.

2. Make `validate` a first-class operation after `create`.

   Validation checks whether prepared worktrees are actually usable as project workspaces. It should verify worktree presence, branch posture, required local-state links, submodule materialization, and project-scope command readiness.

   Alternative considered: fold validation into `create`. That hides readiness failures inside setup and makes it harder to rerun validation after local state or project tools change.

3. Keep the top-level entrypoint short and structured.

   `SKILL.md` should contain activation, help, operation table, routing table, shared constraints, and pointer references. It should not contain long local-state or submodule procedures.

   Alternative considered: keep detail inline and add headings. That reduces file movement, but does not solve routing noise.

4. Keep the workspace-manager independent.

   Workspace summaries should be phrased for humans, scripts, or upstream planners. The skill should not say that its summaries are loop-facing or that bookkeeping requests come from loop execplans. `houmao-agent-loop-pro` may depend on workspace-manager from its own pages, but the dependency direction should not be reversed in workspace-manager text.

   Alternative considered: explicitly design the manager around loop-pro. That would make the utility less reusable and contradict its role as a general workspace-preparation skill.

5. Validate local-state completeness as part of project readiness.

   Worktree creation must not leave necessary project state unlinked. `create` should produce and apply a local-state link/materialization plan. `validate` should check that required links exist, point to expected sources, do not replace tracked content, and allow configured project commands to run from the worktree.

## Risks / Trade-offs

- Existing callers may still ask for `execute` → Keep `execute` as a compatibility alias for `create` in help/routing during a transition.
- Validation commands may create normal project cache/build outputs → Document validation as avoiding workspace topology mutation, not as filesystem-pure.
- Automatic command discovery may run expensive or unsafe commands → Prefer explicit operator-supplied validation commands and conservative probes; require confirmation before heavy or destructive commands.
- Splitting files can make guidance harder to find → Provide a clear operation table and routing table in `SKILL.md`, and keep reference page names obvious.
