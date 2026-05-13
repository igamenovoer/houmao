# Validate Loop

## Read First

- `../reference/generated-contract-defaults.md`
- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`

## Preconditions

- Generated execplan exists.
- Operator wants to check concrete pre-launch readiness before `launch-agents`.

## Inputs

Require:
- `<loop-dir>`
- `<loop-dir>/execplan/manifest.toml`
- generated execplan validation evidence or a current `validate-execplan` pass
- prepared agent/profile facts from `prepare-agents`
- prepared workspace facts from `prepare-workspace`, or explicit equivalent manual workspace evidence, when managed workspaces are required

Use when present:
- generated agent bindings;
- generated workspace contracts;
- generated run artifact contracts;
- generated harness docs or commands;
- mailbox, gateway, notifier, memory, and inspection posture reports.

## Checks

1. Confirm the generated execplan is validated enough for execution.
2. Confirm concrete agent/profile identities and launch profile facts exist for every required participant.
3. Confirm generated and private skills are installed or project-scoped as required by agent bindings.
4. Confirm maintained support skills are bound for each participant's responsibilities.
5. When managed workspaces are required, confirm workspace facts from `prepare-workspace` or explicit manual evidence match prepared agent/profile names, generated workspace contracts, and generated agent bindings.
6. Confirm launch profile cwd and memo seed posture match workspace contracts when workspace setup adjusted those facts.
7. For mail-driven loops, confirm mailbox, gateway, notifier prompt, and mail support posture are ready.
8. Confirm generated notifier prompts tell agents which on-event skill to use and whether to run a follow-up on-tick skill after mail processing.
9. Confirm generated skills can locate the plan-local harness when they depend on dynamic objective, constraint, policy, state, schema, rendering, query, validation, or controlled-apply commands.
10. Confirm required harness commands or import posture are usable enough for launch and start.
11. Confirm run artifact directories, run id policy, payload paths, record paths, state paths, logs, evidence paths, and operator-note paths are ready when the execplan defines them.
12. Confirm state initialization is complete or has an explicit start-time initialization path.
13. Confirm participants are launchable; do not require live managed-agent sessions before `launch-agents`.
14. Confirm no generated runtime behavior asks agents to sleep, poll, tail logs, or wait in-chat for future mail or ticks.

## Report

Report:
- readiness result: ready, ready with warnings, or blocked;
- prepared agent/profile facts checked;
- workspace facts, manual workspace evidence, or no-workspace posture checked;
- generated skill and maintained support skill posture;
- mailbox, gateway, notifier, and memory posture;
- harness and run artifact posture;
- state initialization posture;
- launchability posture;
- blockers that must be fixed before `launch-agents`;
- warnings that do not block `launch-agents`;
- whether `launch-agents` may proceed.

## Constraints

- Do not mutate agent profiles, workspaces, mailboxes, gateways, harness state, run artifacts, or live agents as the normal validation path.
- Do not repair missing preparation from this page.
- Do not require agents to already be live; that is checked by `launch-agents` and `start`.
- Do not start loop work.
- Do not treat `validate-execplan` as a substitute for concrete runtime readiness.
- Do not ask agents to wait in-chat for later mail or tick work.
