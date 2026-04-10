# Live Operations Branch

Use this branch when the user wants to try post-launch operations against one already-running managed agent.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Confirm which live managed agent the user wants to work with.
3. Route the selected live-operation branch:
   - normal prompt entry -> `houmao-agent-messaging`
   - generic live state, screen, mailbox-posture, or artifact inspection -> `houmao-agent-inspect`
   - ordinary mailbox send or read entry -> `houmao-agent-email-comms`
   - gateway mail-notifier enable, disable, or status -> `houmao-agent-gateway`
   - reminders -> `houmao-agent-gateway`
4. When ordinary mailbox work needs current live bindings or the exact current `gateway.base_url`, let `houmao-agent-messaging` or `houmao-agent-email-comms` resolve that through `houmao-mgr agents mail resolve-live`.
5. When current tour context already shows that a live gateway is attached and mailbox accounts are set up, explicitly suggest gateway `mail-notifier` as a useful next step because it lets the agent check unread email automatically in the background.
6. After the selected live operation completes, summarize the result and offer the next likely branches:
   - send another prompt
   - inspect live state or screen posture
   - send or read mailbox work
   - enable automatic email notification through gateway `mail-notifier`
   - create a reminder
   - stop, relaunch, or clean up the agent
   - create another specialist or launch another agent

## Guardrails

- Do not treat reminders as durable recovered state; keep their durability description on `houmao-agent-gateway`.
- Do not treat ordinary mailbox send or read work as part of the gateway-only control surface.
- Do not guess the live agent target or the current gateway base URL.
