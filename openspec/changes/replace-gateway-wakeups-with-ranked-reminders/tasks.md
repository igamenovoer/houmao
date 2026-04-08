## 1. Gateway Reminder API

- [ ] 1.1 Replace wakeup request and response models in `src/houmao/agents/realm_controller/gateway_models.py` with reminder create, batch-create, list, get, update, and delete schemas, including title, prompt, ranking, paused, and selection-versus-delivery state fields.
- [ ] 1.2 Update `src/houmao/agents/realm_controller/gateway_client.py` and the live FastAPI route declarations in `src/houmao/agents/realm_controller/gateway_service.py` to remove `/v1/wakeups` and expose the `/v1/reminders` route family instead.

## 2. Gateway Runtime Arbitration

- [ ] 2.1 Refactor the in-memory wakeup record and scheduler state in `src/houmao/agents/realm_controller/gateway_service.py` into reminder records with deterministic ranking order, effective-reminder selection, and paused blocking behavior.
- [ ] 2.2 Rework reminder execution and rescheduling so only the effective reminder can dispatch, readiness gating remains unchanged, repeating reminders keep no-burst cadence, and reminder update or delete operations recompute the effective reminder immediately.
- [ ] 2.3 Rename or replace wakeup-specific gateway event, logging, and inspection helpers so runtime diagnostics describe reminders and effective-reminder state consistently.

## 3. Skill And Docs Alignment

- [ ] 3.1 Update the packaged `houmao-agent-gateway` system skill assets to replace wakeup guidance with reminder guidance, including route rename, ranking semantics, paused blocking behavior, and any action-document renames needed under the skill asset tree.
- [ ] 3.2 Update maintained gateway contract and CLI/system-skill docs to describe `/v1/reminders` as the direct live reminder surface and to remove stale `/v1/wakeups` terminology where this change affects supported behavior.
- [ ] 3.3 Verify that the refactor does not introduce unsupported `houmao-mgr agents gateway reminders ...` commands or managed-agent `/houmao/agents/{agent_ref}/gateway/reminders` projections, and keep the docs explicit about the direct live HTTP boundary.

## 4. Verification

- [ ] 4.1 Update gateway unit tests for models and runtime behavior to cover batch reminder creation, ranking tie-breaking, paused effective blocking, reminder updates, repeating reminder cadence, and reminder 404 or 422 error cases.
- [ ] 4.2 Update integration tests and any maintained skill or doc assertions that currently reference `/v1/wakeups` so they validate the `/v1/reminders` contract instead.
- [ ] 4.3 Run the focused gateway and system-skill test suites affected by the refactor and record the verification results for the change.
