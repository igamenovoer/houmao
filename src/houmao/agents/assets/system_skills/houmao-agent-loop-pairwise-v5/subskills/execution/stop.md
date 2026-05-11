# Stop

Use this page when the operator wants to end one v5 loop run.

## Inputs

Require:
- `<loop-dir>`
- run identity
- desired stop posture when the user has one

## Procedure

1. Validate enough execplan context to identify generated stop guidance.
2. Use generated harness or generated operator skill stop surfaces when available.
3. Route managed-agent lifecycle stop work through `houmao-agent-instance`.
4. Route final prompts, mailbox notices, or interrupts through `houmao-agent-messaging` or `houmao-agent-email-comms`.
5. Route gateway notifier shutdown or reminder cleanup through `houmao-agent-gateway`.
6. Run a final read-only status check and report stopped participants, retained artifacts, and cleanup options.

## Boundaries

- Do not delete `<loop-dir>/intention/` or `<loop-dir>/execplan/`.
- Do not cleanup stopped-session artifacts unless the user asks for cleanup.
- Do not redefine stop as hard-kill unless the user asks for emergency interruption.
