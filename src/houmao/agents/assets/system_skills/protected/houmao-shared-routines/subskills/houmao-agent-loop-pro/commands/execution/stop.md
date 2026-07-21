# Stop

## Read First

- MUST READ: `../reference/runtime-mail-model.md`
- `../reference/platform-boundaries.md`
- `../reference/system-input-questions.md`

## Preconditions

- Operator wants to end one loop run.

## Inputs

Require:
- `<loop-dir>`
- run identity
- desired stop posture when the user has one

## Actions

1. Validate enough execplan context to identify generated stop guidance.
2. Use generated operator-control guidance or harness `control stop` surfaces when available.
3. Route managed-agent lifecycle stop work through `<public-entrypoint>->houmao-shared-routines->agent-instance`.
4. Route final prompts, mailbox notices, or interrupts through `<public-entrypoint>->houmao-shared-routines->agent-messaging` or `<public-entrypoint>->houmao-shared-routines->agent-email-comms`.
5. Route gateway notifier shutdown or reminder cleanup through `<public-entrypoint>->houmao-shared-routines->agent-gateway`.
6. Run a final read-only status check and report stopped participants, final execution mode or notifier posture when known, retained artifacts, and cleanup options.

## Constraints

- Do not delete `<loop-dir>/intention/` or `<loop-dir>/execplan/`.
- Do not cleanup stopped-session artifacts unless the user asks for cleanup.
- Do not redefine stop as hard-kill unless the user asks for emergency interruption.
