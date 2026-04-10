## 1. Update pairwise lifecycle guidance

- [x] 1.1 Revise `houmao-agent-loop-pairwise` top-level guidance so the operator-facing lifecycle actions are named `plan`, `initialize`, `start`, `peek`, `ping`, `pause`, `resume`, and `stop`, while still mapping cleanly onto the existing authoring, prestart, and operating lanes.
- [x] 1.2 Update the pairwise prestart and operating pages so `initialize`, `peek`, `ping`, `pause`, `resume`, and `stop` have explicit semantics, including `peek master|all|<agent-name>`, read-only `peek` versus active `ping`, and master-directed `stop`.
- [x] 1.3 Update pairwise templates and references so the canonical observed state names `authoring`, `initializing`, `awaiting_ack`, `ready`, `running`, `paused`, `stopping`, `stopped`, and `dead` are documented separately from lifecycle actions.

## 2. Align boundary docs and tests

- [x] 2.1 Update the relevant system-skill overview or related loop docs so they use the same canonical pairwise lifecycle action and state vocabulary.
- [x] 2.2 Update unit coverage for packaged pairwise skill content so tests assert the new lifecycle action names, the read-only `peek` contract, the active `ping` contract, and the distinct observed state vocabulary.
- [x] 2.3 Clarify in pairwise docs and tests that canonical `stop` is master-directed and that any participant-wide advisory stop broadcast is separate if documented at all.

## 3. Validate the vocabulary change

- [x] 3.1 Run targeted validation for the touched pairwise skill and documentation tests.
- [x] 3.2 Record the resulting verification evidence in the change work before apply or archive.

## 4. Verification Evidence

- 2026-04-10: `pixi run ruff check tests/unit/agents/test_system_skills.py` -> passed
- 2026-04-10: `pixi run pytest tests/unit/agents/test_system_skills.py` -> passed (`17 passed`)
