## 1. Package The V4 Skill

- [x] 1.1 Create `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v4/` as a packaged sibling of pairwise-v3 with v4 skill identity, frontmatter, UI metadata, and manual-invocation wording.
- [x] 1.2 Preserve the pairwise-v3 lifecycle pages, workspace-contract references, memo-first initialize guidance, mail-notifier readiness guidance, mail-first start guidance, and runtime-owned recovery boundaries in v4.
- [x] 1.3 Add v4-specific authoring guidance for source-constraint extraction, projection, and coverage audit before final bundle output.
- [x] 1.4 Add bundled strict document-template references for canonical `plan.md`, role-local agent notes, reporting templates, bookkeeping templates, and constraint coverage audit.

## 2. Implement Strict Template Authoring

- [x] 2.1 Update v4 `authoring/formulate-loop-plan.md` so rich task-note planning fills required template slots instead of freeform-organizing generated files.
- [x] 2.2 Update v4 plan-structure and bundle-template references to require a central source-contract summary and carried-forward constraints table in `plan.md`.
- [x] 2.3 Update v4 agent-note template guidance so lead/reviewer/coder/generic participant notes include role, source constraints carried forward, hard gates, SOP verbs, reporting/evidence duties, and related skill posture.
- [x] 2.4 Update v4 reporting and bookkeeping template guidance so state schemas and evidence/reporting requirements from source tasks become reusable generated templates.
- [x] 2.5 Add a v4 coverage-audit template and authoring rule that maps each extracted high-salience source rule to central and runtime projections or marks it unresolved with a reason.

## 3. Register And Document The Skill

- [x] 3.1 Add `houmao-agent-loop-pairwise-v4` to `src/houmao/agents/assets/system_skills/catalog.toml` and include it in both `core` and `all`.
- [x] 3.2 Update README loop-skill and system-skill tables plus managed-home/default-install wording to include all four pairwise variants and all five loop skills.
- [x] 3.3 Update `docs/getting-started/loop-authoring.md` so readers know when to choose v4 over v3.
- [x] 3.4 Update `docs/getting-started/system-skills-overview.md` so the packaged skill catalog includes v4 exactly once.
- [x] 3.5 Update touring or generic-loop cross references only if tests reveal current "choose among pairwise skills" language became stale.

## 4. Tests And Validation

- [x] 4.1 Update system-skill catalog/install tests, brain-builder tests, and CLI system-skills tests for the new v4 catalog member and default resolved sets.
- [x] 4.2 Add assertions that installed v4 assets include strict document templates, source-constraint extraction/projection language, policy-bearing verbs, and coverage-audit guidance.
- [x] 4.3 Update docs tests so loop-authoring and overview docs mention v4 and still distinguish v3 workspace-aware planning from v4 template-driven planning.
- [x] 4.4 Run focused tests for system skills, brain builder, CLI system-skill listing/install, and docs coverage.
- [x] 4.5 Run `openspec validate add-pairwise-v4-template-loop-skill --strict` and resolve any spec or task-format issues.
