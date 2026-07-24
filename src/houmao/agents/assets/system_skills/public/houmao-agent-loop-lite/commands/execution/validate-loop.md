# Validate Loop

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

## Read First

- `../reference/markdown-contract-defaults.md`
- `../reference/markdown-template-events.md`
- `../reference/direct-sqlite-state.md`
- `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

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
