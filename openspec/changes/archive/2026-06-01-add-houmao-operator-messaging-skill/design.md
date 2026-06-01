## Context

Houmao currently has skills for direct managed-agent communication (`houmao-agent-messaging`) and mailbox operations (`houmao-agent-email-comms`). Those skills are last-mile operational tools: they route a known prompt or mailbox note to a known agent through known transport facts.

Operators increasingly need a higher-level manual control surface that can clarify a task, decide whether one or many agents should receive messages, select direct prompt or mailbox transport, and keep enough record of the clarified intent to make dispatch reviewable. Generated loop skills cover durable orchestration, but they are intentionally heavier than temporary operator-directed messaging.

## Goals / Non-Goals

**Goals:**

- Add a standalone manual-only `houmao-operator-messaging` skill.
- Make `clarify` a first-class subcommand that never dispatches.
- Make `dispatch` handle one or many targets from the user's task without separate single/multi subcommands.
- Default dispatch to prompt delivery, using mailbox only when the operator prompt or chat context asks for mail-style delivery.
- Reuse `houmao-agent-messaging` and `houmao-agent-email-comms` for last-mile delivery.
- Support clarified-intent records in chat memory by default, or in a user-specified Markdown file when requested.
- Include the new skill in the packaged Houmao system-skill catalog and default relevant skill sets.

**Non-Goals:**

- Do not create a durable loop engine, scheduler, retry system, or topology validator.
- Do not replace direct messaging, mailbox, gateway, lifecycle, inspection, or loop skills.
- Do not invent target agents, gateway URLs, mailbox identities, or external Markdown paths.
- Do not add runtime APIs or change mailbox storage formats.

## Decisions

### Add a New Skill Instead of Extending Agent Messaging

`houmao-agent-messaging` remains focused on managed-agent communication and control. `houmao-operator-messaging` owns the higher-level operator interaction: clarify intent, decide target scope, produce dispatch packets, and delegate delivery.

Alternative considered: add `clarify` and multi-target behavior to `houmao-agent-messaging`. That would blur last-mile delivery with operator orchestration and make the existing direct-operation skill harder to reason about.

### Keep the Skill Manual-Only

The new skill is invoked only when the user explicitly selects `houmao-operator-messaging` or names one of its operations. Generic requests such as "tell the coder" can still be handled by existing direct messaging workflows unless the operator explicitly wants the clarification/dispatch layer.

Alternative considered: auto-route any operator-to-agent wording to the new skill. That would surprise users who expect simple direct messaging and could cause unnecessary clarification loops.

### Split Clarification and Dispatch

`clarify` records intent and asks bounded, high-impact questions without sending messages. `dispatch` consumes clarified intent from chat memory or a user-specified Markdown file, asks only blocking questions, and then sends through the appropriate lower-level skill.

Alternative considered: make dispatch always run full clarification first. That would make a side-effecting operation harder to predict and could slow down well-specified commands.

### Treat Single-Agent and Multi-Agent Dispatch as Dispatch Policy

The user task determines whether dispatch reaches one agent or multiple agents. The skill exposes one `dispatch` subcommand and lets the command packet plan express target count, ordering, transport, and reply expectations.

Alternative considered: add `dispatch-one` and `dispatch-many`. Separate subcommands would encode routing mechanics into the interface even though the meaningful choice is the operator's task intent.

### Default Dispatch to Prompt Delivery

`dispatch` uses prompt delivery unless the operator prompt or chat context indicates mailbox delivery. Prompt dispatch delegates to `houmao-agent-messaging`, which owns the gateway-preferred prompt route: use the target gateway when available, otherwise use the direct managed-agent prompt fallback with forced fallback behavior where the selected prompt surface supports it.

Alternative considered: select mailbox whenever a target has a mailbox. That would make mailbox availability override operator intent and turn ordinary operator commands into asynchronous mail without asking.

### Use Existing Mailbox Identity Semantics

For mailbox dispatch, a Houmao-managed operator with a usable mailbox uses its own mailbox address for ordinary sends. An external operator, or a current operator without a usable own mailbox, uses the supported operator-origin mailbox post path where available. Required mailbox routing blocks if the target or transport cannot support it.

Alternative considered: always use the reserved operator-origin sender. That would discard useful managed-agent identity when the operator is itself part of the Houmao runtime.

## Risks / Trade-offs

- Skill wording may accidentally duplicate low-level messaging documentation -> Keep entrypoint language concise and route delivery details to existing skills.
- Operators may expect `dispatch` to orchestrate retries or follow-up ordering over time -> State the boundary clearly and recommend loop skills for durable orchestration.
- External Markdown records can become stale relative to chat memory -> Require the user to supply the path explicitly and append/update the record when that mode is selected.
- Catalog changes can miss install tests -> Update catalog fixture expectations and packaged skill installation tests with the new skill.
