## 1. Revise v2 preparation targeting

- [x] 1.1 Update `houmao-agent-loop-pairwise-v2/SKILL.md` and `prestart/prepare-run.md` so `initialize` targets delegating/non-leaf participants by default instead of every participant.
- [x] 1.2 Document the explicit override for preparing leaf agents, preparing all participants, or naming leaf participants in the preparation target set.
- [x] 1.3 Define `require_ack`, `awaiting_ack`, and `ready` in terms of the actual targeted preparation recipients.

## 2. Align authoring and plan surfaces

- [x] 2.1 Update v2 authoring guidance to keep participant preparation material for all participants while distinguishing it from default preparation mail recipients.
- [x] 2.2 Update `references/plan-structure.md`, `templates/single-file-plan.md`, and `templates/bundle-plan.md` to record preparation targets and the leaf-preparation override.
- [x] 2.3 Update `references/run-charter.md` and `operating/start.md` so start validation treats targeted preparation completion as the readiness barrier.

## 3. Refresh verification coverage

- [x] 3.1 Update packaged system-skill tests to assert delegator-default preparation, explicit leaf override, targeted acknowledgement handling, and unclear-topology fallback wording.
- [x] 3.2 Run targeted verification for the v2 system-skill content after the guidance is updated.
