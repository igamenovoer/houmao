## 1. Update pairwise-v3 authoring contracts

- [x] 1.1 Revise the pairwise-v3 skill guidance and authoring pages so bundle plans can include a generated `<plan-output-dir>/templates/` directory when reusable reporting or bookkeeping scaffolds are needed.
- [x] 1.2 Update the pairwise-v3 bundle-plan and plan-structure references to document the template directory, its discoverable categories, and the rule that template-bearing runs use bundle form rather than single-file form.
- [x] 1.3 Update the pairwise-v3 reporting and workspace-contract guidance so generated reporting templates derive from the reporting contract, bookkeeping templates remain task-shaped, and authored templates stay distinct from mutable bookkeeping outputs and runtime-owned recovery files.

## 2. Teach the skill what templates to generate

- [x] 2.1 Update pairwise-v3 authoring instructions and templates so the planner generates sensible reporting templates for the applicable run surfaces such as peek, completion, recovery, stop, and hard-kill summaries.
- [x] 2.2 Update pairwise-v3 authoring instructions and templates so the planner generates sensible bookkeeping templates from the task objective, topology, participant roles, and declared bookkeeping paths without imposing one fixed subtree.
- [x] 2.3 Ensure the canonical `plan.md` surface and supporting bundle files reference the generated template inventory clearly enough for operators and participants to find and use it.

## 3. Refresh documentation and verify the change

- [x] 3.1 Update `docs/getting-started/loop-authoring.md` to explain when pairwise-v3 bundle plans should carry plan-owned templates and how those templates relate to bookkeeping paths and runtime-owned recovery files.
- [x] 3.2 Review the updated pairwise-v3 assets for consistency so `SKILL.md`, authoring pages, references, and templates all describe the same plan-owned template boundaries and bundle behavior.
- [x] 3.3 Run the relevant repository checks for the touched documentation and Markdown assets, and confirm the change artifacts and docs are ready for implementation review.
