# Schedule Self-Publication at Idle

A managed agent can save a plugin update during a turn. Publication can require idle native maintenance, so every immediate attempt from inside the agent's turn can return `busy`. Accept an explicit, one-shot publication intent from the verified managed runtime and dispatch it at a qualified idle boundary.

## Status

Accepted.

## Consequences

The gateway retains the original publisher, exact candidate, expected base, and authorization evidence. It rechecks them at handoff. Authority loss or a moved base ends the intent and preserves the saved candidate. The operation ID tracks pending work, publication, and native activation through the normal receipt path.
