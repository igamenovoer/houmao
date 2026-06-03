# Live Operations Branch

Use this intermediate branch when the user wants to operate or coordinate one or more already-running managed agents.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Confirm which live managed agent or agents the user wants to work with. If the target is unclear, route discovery to `houmao-agent-inspect`.
3. Help the user choose the communication or operation mode before routing:
   - normal direct prompt, interrupt, raw input, or mailbox handoff routing -> `houmao-agent-messaging`
   - managed-agent memo, pages, or profile memo-seed context -> `houmao-memory-mgr`
   - ordinary mailbox send, read, reply, post, move, or archive -> `houmao-agent-email-comms`
   - operator-origin mail or prompt injection via mail -> `houmao-agent-email-comms`
   - one gateway-notified open-mail processing round with a prompt-provided gateway base URL -> `houmao-process-emails-via-gateway`
   - generic live state, screen, mailbox-posture, logs, turn-state, or artifact inspection -> `houmao-agent-inspect`
   - gateway lifecycle, TUI watch, mail-notifier enable/disable/status, or reminders -> `houmao-agent-gateway`
4. When ordinary mailbox work needs current live bindings or the exact current `gateway.base_url`, let `houmao-agent-messaging` or `houmao-agent-email-comms` resolve it. For the caller's own managed session, use `houmao-mgr agents self mail resolve-live`. For a selected agent, use `houmao-mgr agents single --agent-name <name> mail resolve-live`.
5. When the prompt is a notifier round and already provides the gateway base URL, route to `houmao-process-emails-via-gateway` rather than rediscovering the gateway here.
6. When current tour context already shows that a live gateway is attached and mailbox accounts are set up, explicitly suggest gateway `mail-notifier` as a useful intermediate next action because it lets the agent wake for open mail.
7. When two or more agents are running, present manual coordination as an intermediate action: send prompts or mailbox messages, inspect responses, update memo context when useful, and only escalate to advanced loop guidance when repeated coordination is emerging.
8. After the selected live operation completes, summarize the result and offer stage-aware next actions:
   - continue the conversation with another prompt
   - inspect live state, screen posture, logs, turn evidence, mailbox posture, or runtime artifacts
   - add or read memo/page context
   - send, read, reply to, post, or archive mailbox work
   - process a notifier-reported mail round when the gateway base URL is provided
   - enable or inspect automatic email notification through gateway `mail-notifier`
   - create a reminder
   - coordinate another running agent manually
   - launch another specialist-backed agent
   - move to advanced loop or isolated workspace guidance only when repeated coordination, generated topology, or workspace isolation is the user's goal
   - stop, relaunch, or clean up an agent through the lifecycle branch

## Mode Guidance

- Use direct prompts for immediate conversational control of a running agent.
- Use mailbox messages when work should be visible in the shared mailbox, delivered between agents, or processed by mailbox-aware workflows.
- Use operator-origin mail when the caller is outside the managed-agent runtime but needs to leave a mailbox-backed instruction for a managed agent.
- Use prompt injection via mail only when the user intentionally wants mailbox content to be the prompt carrier for an agent or notifier-driven workflow.
- Use notifier-round processing only for one open-mail round reported by gateway mail-notifier and only when the current prompt supplies the exact gateway base URL.
- Use memo and pages for durable working context, not as a queue, mailbox, gateway reminder, or runtime bookkeeping store.

## Guardrails

- Keep the durability description of reminders on `houmao-agent-gateway`; do not treat them as durable recovered state.
- Do not treat ordinary mailbox send or read work as part of the gateway-only control surface.
- Never guess the live agent target or the current gateway base URL.
- Do not rediscover a missing gateway base URL inside a notifier-round workflow; route only when the round provides it.
- Generated loop authoring is not the default solution for one-off manual coordination.
