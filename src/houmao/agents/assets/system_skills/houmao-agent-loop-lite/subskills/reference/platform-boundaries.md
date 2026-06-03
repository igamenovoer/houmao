# Platform Boundaries

## Maintained Surfaces

- Agent definitions and profiles: `houmao-agent-definition`.
- Workspace planning, creation, validation, and summaries: `houmao-utils-workspace-mgr`.
- Launch, join, stop, and relaunch: `houmao-agent-instance`.
- Ordinary mail send, reply, read, and archive work: `houmao-agent-email-comms` or supported mailbox CLI surfaces.
- Gateway and notifier lifecycle: `houmao-agent-gateway`.
- Prompt, interrupt, and live managed-agent messages: `houmao-agent-messaging`.
- Liveness, logs, mailbox posture, gateway posture, and runtime inspection: `houmao-agent-inspect`.

## Constraints

- Do not duplicate maintained Houmao contracts inside lite specs or generated skills.
- Do not invent `houmao-mgr` surfaces.
- Use `plan`, `create`, `validate`, or `summarize` for workspace-manager operations; do not use legacy `execute` wording.
