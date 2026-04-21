## 1. Revise pairwise-v3 lifecycle assets

- [x] 1.1 Update `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v3/SKILL.md` to describe memo-first `initialize`, lightweight master-only `start`, and the removal of ordinary start-time `accepted` / `rejected`.
- [x] 1.2 Update `prestart/prepare-run.md`, `operating/start.md`, and `references/run-charter.md` so v3 no longer depends on durable initialize pages or durable start-charter pages for ordinary start.
- [x] 1.3 Update any v3 recovery-facing guidance that still assumes ordinary start created start-charter material, replacing those references with memo-first run material expectations.

## 2. Revise v3 authoring and docs

- [x] 2.1 Update v3 authoring guidance and plan templates to record memo-first initialize behavior, memo-slot expectations, and the revised lifecycle vocabulary.
- [x] 2.2 Update `docs/getting-started/loop-authoring.md` and other relevant overview/reference docs so pairwise-v3 is described as memo-first rather than as a start-charter-based extension of pairwise-v2.
- [x] 2.3 Update any examples or reference text that tell operators to wait for ordinary v3 `start` to return `accepted` or `rejected`.

## 3. Validate the revised OpenSpec contract

- [x] 3.1 Verify the changed skill assets and docs are internally consistent about the new initialize/start boundary.
- [x] 3.2 Run `pixi run openspec validate simplify-pairwise-v3-memo-first-start --strict`.
