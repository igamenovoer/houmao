## 1. Revise Pairwise-V2 Skill Assets

- [x] 1.1 Update `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/SKILL.md` and `agents/openai.yaml` so pairwise-v2 describes `precomputed_routing_packets` as the default prestart strategy, durable memo/page materialization during `initialize`, a compact page-backed `start` trigger, and a user-selected plan output directory with `plan.md` as the canonical entrypoint.
- [x] 1.2 Revise `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/prestart/prepare-run.md` to define participant initialize pages, exact-sentinel memo reference blocks, fail-closed replacement rules, and `operator_preparation_wave` as the only mail-first lane.
- [x] 1.3 Revise `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/operating/start.md` and `references/run-charter.md` so `start` writes a durable master charter page plus memo reference block before sending a compact control-plane trigger.

## 2. Align Supporting Pairwise-V2 Guidance

- [x] 2.1 Update `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v2/references/plan-structure.md` and any related pairwise-v2 references to describe run-scoped initialize/start pages, bounded memo reference blocks, and the expected output-directory structure where the plan or charter structure depends on them.
- [x] 2.2 Update `docs/getting-started/loop-authoring.md` so the user-facing pairwise-v2 guide matches the packet-first default `initialize`, page-backed durable guidance, and compact `start` trigger semantics.

## 3. Verify Skill And Docs Contracts

- [x] 3.1 Update `tests/unit/agents/test_system_skills.py` to assert the revised pairwise-v2 skill, prestart, and start guidance text, including the packet-first default and durable memo/page wording.
- [x] 3.2 Add or update a docs-focused unit test that guards the loop-authoring guide against regressing back to email-first default initialization wording.
- [x] 3.3 Run the relevant unit test slices for system skills and docs, and confirm the changed pairwise-v2 assets are consistent with the new spec delta.
