# Platform Boundaries

## Maintained Surfaces

- Agent definitions and profiles: `<public-entrypoint>->houmao-shared-routines->agent-definition`.
- Workspace planning, creation, validation, and summaries: `<public-entrypoint>->houmao-shared-routines->utils-workspace-mgr`.
- Launch, join, stop, and relaunch: `<public-entrypoint>->houmao-shared-routines->agent-instance`.
- Ordinary mail send, reply, read, and archive work: `<public-entrypoint>->houmao-shared-routines->agent-email-comms` or supported mailbox CLI surfaces.
- Gateway and notifier lifecycle: `<public-entrypoint>->houmao-shared-routines->agent-gateway`.
- Prompt, interrupt, and live managed-agent messages: `<public-entrypoint>->houmao-shared-routines->agent-messaging`.
- Liveness, logs, mailbox posture, gateway posture, and runtime inspection: `<public-entrypoint>->houmao-shared-routines->agent-inspect`.

## Constraints

- Do not duplicate maintained Houmao contracts inside lite specs or generated skills.
- Do not invent `houmao-mgr` surfaces.
- Use `plan`, `create`, `validate`, or `summarize` for workspace-manager operations; do not use legacy `execute` wording.
