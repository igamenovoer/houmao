# Messaging Intent Matrix

Use this table when you know what you want to do but need the supported Houmao surface that matches that intent.

| Intent | Preferred CLI Surface | Preferred HTTP Surface | Notes |
| --- | --- | --- | --- |
| Discover target and capability | `agents state`, `agents gateway status`, `agents mail resolve-live` | `GET /houmao/agents/{agent_ref}`, `GET /gateway`, `GET /mail/resolve-live` | Use this first when gateway or mailbox availability is uncertain. |
| Ordinary prompt turn | `agents gateway status`, then `agents gateway prompt` when a live gateway exists, otherwise `agents prompt` | `GET /gateway`, then prefer `POST /houmao/agents/{agent_ref}/gateway/control/prompt` when a live gateway exists, otherwise `POST /houmao/agents/{agent_ref}/requests` | Check gateway first and prefer gateway-backed prompt delivery when available. |
| Transport-neutral interrupt | `agents interrupt` | `POST /houmao/agents/{agent_ref}/requests` | Use this for ordinary interrupt requests across TUI and headless transports. |
| Explicit gateway queue prompt or interrupt | `agents gateway prompt`, `agents gateway interrupt` | `POST /houmao/agents/{agent_ref}/gateway/requests` | Use only when live-gateway queue semantics matter. |
| Gateway-owned TUI inspection or prompt provenance | `agents gateway tui state|history|note-prompt` | `GET /gateway/tui/state`, `GET /gateway/tui/history`, `POST /gateway/tui/note-prompt` | Inspection and provenance, not the default prompt-turn path. |
| Exact raw control input | `agents gateway send-keys` | `POST /houmao/agents/{agent_ref}/gateway/control/send-keys` | Use for slash menus, arrows, `Escape`, or partial typing. |
| Mailbox handoff | `agents mail resolve-live` | `GET /mail/resolve-live` | Use discovery here, then hand off to `houmao-agent-email-comms` for ordinary mailbox work or `houmao-process-emails-via-gateway` for one unread-email round. |
| Reset context and send immediately | no first-class CLI flag today | `POST /houmao/agents/{agent_ref}/gateway/control/prompt` with `chat_session.mode = "new"` | Direct gateway `/v1/control/prompt` is lower-level fallback only when the exact live base URL is already known. |
| Prepare next headless prompt session without sending now | no first-class CLI flag today | `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` | Direct gateway `/v1/control/headless/next-prompt-session` is the lower-level fallback only when the exact live base URL is already known. |
