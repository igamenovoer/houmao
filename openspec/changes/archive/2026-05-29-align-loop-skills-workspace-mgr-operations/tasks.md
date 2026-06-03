## 1. Pro Prepare-Workspace Routing

- [x] 1.1 Update `houmao-agent-loop-pro/subskills/execution/prepare-workspace.md` to use workspace-manager operations `plan`, `create`, `validate`, and `summarize`.
- [x] 1.2 Replace stale `execute` operation extraction/report wording with `create`, while documenting `execute` only as legacy input normalized to `create`.
- [x] 1.3 Update prepare-workspace postconditions and reports to distinguish planned, created, validated, summarized, missing, inconsistent, and custom/manual workspace facts.
- [x] 1.4 Ensure prepare-workspace treats a plan-only result as not launch-ready when managed workspace readiness is required.

## 2. Pro Workspace Contract Guidance

- [x] 2.1 Update `execplan-specs-contract.md` workspace contract fields and examples to use `shared-kb/`, `owner-states/<subdir>/...`, per-agent `states/`, and per-agent `repo/` surfaces for standard in-repo workspaces.
- [x] 2.2 Replace old standard workspace examples for task `runs/`, task `artifacts/`, per-agent `artifacts/`, ignored `tmp/`, and `needs_kb` with current workspace-manager surfaces or explicit custom/manual workspace guidance.
- [x] 2.3 Add project-scope validation command inputs to pro workspace contract guidance for explicit operator commands and documented safe project commands.
- [x] 2.4 Update generated-contract defaults and reference execplan pattern docs to describe workspace-manager `plan`/`create`/`validate` inputs and current in-repo bookkeeping surfaces.

## 3. Pro Validation And Boundary References

- [x] 3.1 Update `validate-execplan.md` workspace contract checks to require planning, creation, validation, and summary routing through `prepare-workspace` and `houmao-utils-workspace-mgr`.
- [x] 3.2 Update `validate-loop.md`, launch/readiness references, or related execution guidance so workspace readiness can rely on workspace-manager `validate`, current summaries/reports, or explicit manual evidence.
- [x] 3.3 Update `platform-boundaries.md` so `houmao-utils-workspace-mgr` owns workspace planning, creation, validation, and summaries.
- [x] 3.4 Narrow `git-worktree-readiness.md` to defer project-scope command validation and local-state completeness to workspace-manager `validate` instead of duplicating broad repair-oriented behavior.

## 4. Lite Alignment

- [x] 4.1 Update `houmao-agent-loop-lite/SKILL.md` platform-boundary guidance to route explicit workspace setup through workspace-manager planning, creation, validation, and summaries.
- [x] 4.2 Ensure lite guidance does not describe workspace-manager `execute` as the standard operation.

## 5. Tests And Verification

- [x] 5.1 Update packaged asset tests to assert loop-pro prepare-workspace uses `plan`, `create`, `validate`, and `summarize`, with `execute` only as legacy alias wording.
- [x] 5.2 Update packaged asset tests to assert pro workspace contract examples use `shared-kb`, `owner-states`, per-agent `states`, validation command inputs, and no old standard `runs`/`artifacts`/`tmp` workspace examples.
- [x] 5.3 Update packaged asset tests to assert lite routes workspace planning, creation, validation, and summaries through `houmao-utils-workspace-mgr`.
- [x] 5.4 Run focused system-skill asset tests.
- [x] 5.5 Run `openspec validate align-loop-skills-workspace-mgr-operations --strict`.
