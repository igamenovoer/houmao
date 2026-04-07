# Messaging Intent Matrix

Use this table when you know what you want to do but need the supported Houmao surface that matches that intent.

| Intent | Preferred CLI Surface | Pair-Managed HTTP Surface | Notes |
| --- | --- | --- | --- |
| Discover target and capability | `agents state`, `agents gateway status`, `agents mail resolve-live` | `GET /houmao/agents/{agent_ref}`, `GET /gateway`, `GET /mail/resolve-live` | Use this first when gateway or mailbox availability is uncertain. |
| Ordinary prompt turn | `agents prompt` | `POST /houmao/agents/{agent_ref}/requests` | Preferred managed-agent seam for normal conversation. |
| Transport-neutral interrupt | `agents interrupt` | `POST /houmao/agents/{agent_ref}/requests` | Use this for ordinary interrupt requests across TUI and headless transports. |
| Explicit gateway queue prompt or interrupt | `agents gateway prompt`, `agents gateway interrupt` | `POST /houmao/agents/{agent_ref}/gateway/requests` | Use only when live-gateway queue semantics matter. |
| Gateway-owned TUI inspection or prompt provenance | `agents gateway tui state|history|note-prompt` | `GET /gateway/tui/state`, `GET /gateway/tui/history`, `POST /gateway/tui/note-prompt` | Inspection and provenance, not the default prompt-turn path. |
| Exact raw control input | `agents gateway send-keys` | `POST /houmao/agents/{agent_ref}/gateway/control/send-keys` | Use for slash menus, arrows, `Escape`, or partial typing. |
| Mailbox follow-up | `agents mail resolve-live|status|check|send|reply|mark-read` | `/houmao/agents/{agent_ref}/mail/*` | Delegate transport-specific detail to the mailbox skills. |
| Reset context and send immediately | no first-class CLI flag today | `POST /houmao/agents/{agent_ref}/gateway/control/prompt` with `chat_session.mode = "new"` | Direct gateway `/v1/control/prompt` is lower-level fallback only when the exact live base URL is already known. |
| Prepare next headless prompt session without sending now | no first-class CLI flag today | `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` | Direct gateway `/v1/control/headless/next-prompt-session` is the lower-level fallback only when the exact live base URL is already known. |
