## 1. Expand pairwise authoring and prestart guidance

- [x] 1.1 Update `houmao-agent-loop-pairwise` top-level guidance so the skill owns pairwise authoring, prestart preparation, and run control, and add the new prestart lane references.
- [x] 1.2 Revise the pairwise authoring templates and reference pages to support standalone participant preparation material, `prestart.md`, and updated single-file versus bundle structure rules.
- [x] 1.3 Update the pairwise operating pages so `start` performs notifier preflight, preparation-mail dispatch, default fire-and-proceed mode, optional acknowledgement-gated mode, and optional timeout-watch guidance that composes `houmao-agent-inspect` without blocking in the same live turn.

## 2. Implement reply-policy-aware operator-origin mail

- [x] 2.1 Extend mailbox protocol and gateway models to represent explicit operator-origin reply policies while preserving explicit operator-origin provenance metadata.
- [x] 2.2 Update filesystem gateway mailbox behavior and the mail-facing command or server surfaces so operator-origin preparation mail can use `reply_policy=none` or `reply_policy=operator_mailbox` and mailbox reply handling follows that policy.
- [x] 2.3 Update mailbox and skill-facing documentation for reserved-operator-mailbox acknowledgement replies and the default no-reply operator-origin posture.

## 3. Remove the generic planner skill and reroute references

- [x] 3.1 Remove the packaged `houmao-loop-planner` skill assets and any packaging or projection expectations that still install or expose that skill.
- [x] 3.2 Update pairwise, relay, inspect, and system-skill overview guidance that still routes pairwise authoring or handoff through `houmao-loop-planner` or describes downstream peeking without `houmao-agent-inspect`.
- [x] 3.3 Remove or revise tests and fixtures that expect `houmao-loop-planner` content or pairwise routing through the removed planner skill.

## 4. Verify behavior and coverage

- [x] 4.1 Add or update unit coverage for packaged pairwise skill content, including standalone preparation guidance, prestart flow, and timeout-watch documentation.
- [x] 4.2 Add or update mailbox behavior tests for operator-origin default no-reply mail and reply-enabled operator-mailbox reply flows.
- [x] 4.3 Run targeted validation for the touched skill, mailbox, and packaging paths and record the resulting evidence in the change work.
