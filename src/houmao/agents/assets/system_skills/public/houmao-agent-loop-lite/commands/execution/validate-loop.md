# Validate Loop

## Workflow

1. Confirm the inherited actor posture, `<loop-dir>` preconditions, and required inputs, loading only the `## Read First` references.
2. Execute `## Checks` within this command's side-effect boundary.
3. Return the structured report (`## Report`) and stop on any unresolved blocker.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this procedure, its owning skill constraints, and the user request, then execute the plan.

## Read First

- [../../references/markdown-contract-defaults.md](../../references/markdown-contract-defaults.md)
- [../../references/markdown-template-events.md](../../references/markdown-template-events.md)
- [../../references/direct-sqlite-state.md](../../references/direct-sqlite-state.md)
- [../../references/runtime-mail-model.md](../../references/runtime-mail-model.md)
- [../../references/platform-boundaries.md](../../references/platform-boundaries.md)
- [../../references/system-input-questions.md](../../references/system-input-questions.md)

## Inputs

Require:
- `<loop-dir>`
- current `validate-execplan` evidence
- prepared agent/profile facts from `prepare-agents`
- workspace facts when workspace setup is required

## Checks

1. Confirm generated lite execplan validation passed.
2. Confirm required participants have prepared launch facts and generated skills.
3. Confirm launch mode, credential, and workdir facts are known or explicitly accepted as manual.
4. Confirm workspace readiness or accepted no-workspace posture.
5. Confirm mail-driven loops have mailbox, gateway, and notifier posture ready.
6. Confirm templates, generated receiver skills, direct SQLite schema, run directories, and state initialization posture are launch-ready.
7. Confirm no generated behavior asks agents to sleep, poll, tail logs, or wait in-chat.

## Report

Report ready, ready with warnings, or blocked; include blockers, warnings, prepared agents, workspace posture, mail/gateway/notifier posture, SQLite/run posture, and whether `launch-agents` may proceed.

## Constraints

- Do not mutate profiles, workspaces, mailboxes, gateways, SQLite state, run artifacts, or live agents.
- Do not require agents to already be live.
