# Structural Mailbox State Versus Actor State

Use this reference when the task mentions mailbox messages and it is unclear whether the operator needs structural inspection or actor-scoped follow-up state.

## Structural Message Inspection

Use these maintained admin commands:

- `houmao-mgr mailbox messages list|get`
- `houmao-mgr project mailbox messages list|get`

Those commands inspect canonical mailbox metadata plus address-scoped structural projection data for one registered mailbox address.

## Actor-Scoped Mailbox Participation

Use `houmao-agent-email-comms` and the maintained `houmao-mgr agents mail ...` surface when the task is about:

- unread, read, answered, archived, and box state
- replying, sending, or checking mail as one managed agent
- message processing through a live gateway facade
- participant-local mutable state such as read, archived, or deleted follow-up

## Guardrail

Do not present structural message inspection as if it were the same thing as open-mail triage for one managed agent.
