## 1. Advanced Pattern Assets

- [x] 1.1 Update `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/SKILL.md` to list the pairwise driver-worker edge-loop pattern and distinguish it from the existing forward relay-loop pattern.
- [x] 1.2 Add a new pairwise edge-loop pattern page under `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/patterns/` that documents the driver and worker roles, local-close message flow, receipt email flow, final-result email flow, and final-result acknowledgement flow.
- [x] 1.3 In the new pairwise edge-loop pattern page, document recursive child edge-loops where a worker may become a driver downstream but must close those child loops locally before replying upstream.
- [x] 1.4 In the new pairwise edge-loop pattern page, document the required local ledger fields, `edge_loop_id`, optional `parent_edge_loop_id`, default storage under `HOUMAO_JOB_DIR`, the rule that `HOUMAO_MEMORY_DIR` is not the default bookkeeping home, check-mail-first resend behavior, worker deduplication, and the rule that drivers arm follow-up then end the current round.
- [x] 1.5 In the new pairwise edge-loop pattern page, document how timing thresholds are sourced: derive from task context and explicit user deadlines when available, and ask the user when a materially important value cannot be chosen sensibly from context.
- [x] 1.6 In the new pairwise edge-loop pattern page, document the default supervision model for many edge-loops: one supervisor reminder, one local ledger, and optional self-mail checkpoint rather than one live reminder per active loop.
- [x] 1.7 In the new pairwise edge-loop pattern page, add concrete text-block templates for edge-loop request text, receipt email, final-result email, final-result acknowledgement, supervisor reminder text, and optional self-mail checkpoint text.

## 2. Validation

- [x] 2.1 Update `tests/unit/agents/test_system_skills.py` to assert that the new pairwise edge-loop pattern asset is packaged and referenced from the advanced-usage skill index.
- [x] 2.2 Update any affected projected-skill or brain-builder assertions so the new advanced-usage asset set remains validated after packaging.
