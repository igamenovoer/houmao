## Why

Houmao has low-level managed-agent messaging and mailbox skills, but no dedicated manual operator layer for clarifying an operator's intent before dispatching one or more messages. As operator control becomes more complex, direct ad hoc prompting risks sending the wrong instruction, using the wrong transport, or losing the clarified intent between runs.

## What Changes

- Add a standalone, manual-only `houmao-operator-messaging` system skill for operator-to-agent messaging workflows.
- Provide concise entrypoint guidance with visible `help`, `clarify`, and `dispatch` subcommands.
- Add a `clarify` subcommand that resolves operator intent, target agent selection, constraints, success criteria, routing preferences, reply expectations, ordering, and record mode without dispatching messages.
- Add a `dispatch` subcommand that consumes clarified intent from chat memory or a user-specified Markdown file, prepares one or more command packets, and dispatches them by direct prompt or mailbox based on the user's task.
- Define mailbox identity selection for dispatch: use the operator agent's own mailbox when the operator is a Houmao-managed agent with a usable mailbox; otherwise use the supported operator-origin mailbox path.
- Keep single-agent versus multi-agent dispatch as part of `dispatch` behavior rather than a separate subcommand.
- Define boundaries with existing skills: use `houmao-agent-messaging` and `houmao-agent-email-comms` for last-mile delivery, and recommend loop skills when the requested work needs durable orchestration rather than temporary operator messaging.
- Update the packaged Houmao system-skill catalog behavior so `houmao-operator-messaging` is included in current installable skills and default relevant skill sets.

## Capabilities

### New Capabilities

- `houmao-operator-messaging-skill`: Manual operator-facing skill for clarifying intent and dispatching messages to one or more Houmao-managed agents.

### Modified Capabilities

- `houmao-system-skill-installation`: The packaged current-system-skill catalog and default set resolution include `houmao-operator-messaging`.

## Impact

- Adds a new packaged system skill under `src/houmao/agents/assets/system_skills/houmao-operator-messaging/`.
- Updates system-skill catalog/configuration and associated catalog tests.
- May add concise documentation or overview references for the new skill.
- Does not change managed-agent runtime APIs, mailbox storage format, or low-level direct messaging semantics.
