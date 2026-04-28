## Why

Rich pairwise-v3 loop plans can flatten operator-critical source constraints into prose and scatter them across supporting files, which makes generated plans hard to audit and easy for runtime agents to misread. A new pairwise-v4 skill should make strict generated document templates the default authoring contract so planners fill required slots, preserve policy-bearing verbs, and project constraints into the right runtime surfaces.

## What Changes

- Add a packaged `houmao-agent-loop-pairwise-v4` system skill as the template-driven successor to pairwise-v3.
- Keep the pairwise-v3 lifecycle and workspace-aware runtime posture: `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, `recover_and_continue`, `stop`, `hard-kill`, standard/custom workspace contracts, memo-first initialize, and mail-first start.
- Add bundled strict document templates for v4 plan bundles, including central plan sections, role-local agent notes, bookkeeping/reporting templates, and a constraint coverage audit.
- Require v4 planning guidance to extract policy-bearing source constraints from rich task notes and referenced rulebooks, preserve schema-like verbs such as `ALWAYS`, `NEVER`, `CHECK`, `RUN`, `READ`, `ANALYZE`, `DECIDE`, `OUTPUT`, `UPDATE`, `COMMIT`, `MERGE`, and `DISPATCH`, and fill the generated templates rather than freeform-organizing the result.
- Add authoring-time coverage checks so every high-salience source constraint is either projected to central and role-local surfaces or explicitly marked as unresolved.
- Register the v4 skill in the packaged system-skill catalog and default `core`/`all` selections.
- Update README and getting-started docs so readers can discover when to choose v4 over v3.

No breaking change is intended: pairwise-v3 remains available for existing workspace-aware plans.

## Capabilities

### New Capabilities

- `houmao-agent-loop-pairwise-v4-skill`: packaged template-driven workspace-aware pairwise loop skill, including strict generated document templates, source-constraint extraction, role-local projection, and coverage-audit requirements.

### Modified Capabilities

- `houmao-system-skill-installation`: include `houmao-agent-loop-pairwise-v4` in the packaged catalog and in the `core` and `all` resolved install sets.
- `docs-loop-authoring-guide`: document pairwise-v4 as the template-driven successor for rich task-note loop plans and explain when to choose it over pairwise-v3.
- `docs-system-skills-overview-guide`: list the new v4 system skill in the packaged skills overview.
- `docs-readme-system-skills`: list the new v4 skill in README system-skills coverage and keep default-install wording current.

## Impact

- Affects packaged system-skill assets under `src/houmao/agents/assets/system_skills/`.
- Affects `src/houmao/agents/assets/system_skills/catalog.toml` and tests that assert resolved system-skill sets.
- Affects loop-authoring and system-skill documentation in `README.md` and `docs/getting-started/`.
- Adds OpenSpec coverage for the new v4 skill contract while preserving pairwise-v3 behavior.
