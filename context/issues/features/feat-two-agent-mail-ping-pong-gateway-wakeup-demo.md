# Feature Request: Two-Agent Mail Ping-Pong And Gateway Wake-Up Demo

## Status
Proposed

## Summary
Add a demo under `scripts/demo/` that teaches the mailbox-backed, gateway-woken, asynchronous interaction pattern between two Houmao-managed agents.

This request is intentionally behavior-oriented rather than implementation-oriented. The goal is to make the user-visible and developer-visible interaction model clear without binding the request to one specific transport, backend, runtime surface, or internal control path used today.

The core teaching example is a ping-pong exchange:
- one agent sends a mailbox message to another agent,
- the sending turn ends immediately after send,
- the receiver is later woken by its gateway when mail becomes actionable,
- the receiver reads the message, performs the requested task, and replies by mail,
- the sender is later woken by its own gateway, reads the reply, and sends the next message,
- the exchange continues for a small fixed number of rounds.

## Why
This demo would be useful for both users and developers because it makes one of the most important Houmao usage patterns concrete:
- agents can coordinate through mailbox-style message passing instead of synchronous direct control,
- gateways are responsible for wake-up and re-entry into later turns,
- a turn can finish after "send mail" instead of waiting inline for the other side,
- the same logical workflow should remain understandable whether participants are headless agents, TUI agents, or a mixed pair.

Today, it is easy to understand isolated pieces such as mailbox operations, gateway notification, or single-agent wake-up flows in isolation. What is still missing as a teaching artifact is a narrow, reproducible, two-agent roundtrip that shows how those pieces fit together as a long-lived conversation pattern.

## Requested Scope
1. Add a runnable demo pack under `scripts/demo/` for two-agent asynchronous mailbox conversation.
2. Support the same logical demo with participant modes that may be:
   - headless plus headless,
   - TUI plus TUI,
   - headless plus TUI,
   - TUI plus headless.
3. Treat mailbox delivery plus gateway wake-up as the primary progression mechanism after the initial kickoff.
4. Provide an automatic workflow that runs the default conversation end to end.
5. Provide a manual or stepwise workflow that lets an operator inspect, pause, continue, and verify the same live demo state.
6. Produce artifacts that let users and developers understand message flow, thread continuity, gateway wake-up behavior, and turn boundaries.
7. Document this demo as an example of the intended Houmao interaction pattern, not just as a narrow one-off test fixture.

## Expected Agent Behaviour
### Participants
- The demo has two logical participants: an initiator and a responder.
- Each participant has its own managed session, mailbox identity, and gateway.
- The participant execution mode may be headless, TUI, or mixed, but the logical conversation contract stays the same.

### Mode Parity
- The demo may be presented with two headless agents, two TUI agents, or one of each.
- Those mode choices may affect how an operator launches or observes the demo, but they should not change the agent-level behaviour contract.
- In every mode combination, the demo should still read as the same asynchronous mailbox conversation with later gateway-driven wake-up.

### Kickoff
- The demo can begin from one explicit kickoff action, typically aimed at the initiator.
- After kickoff, the conversation should be able to progress primarily through mailbox delivery and gateway wake-up rather than requiring a direct manual prompt submission for every turn.

### Turn Model
- When an agent sends a mailbox message, that agent does not wait inline for the reply.
- Sending the message is treated as sufficient completion for that turn.
- The next time that agent acts should normally happen because its gateway observes actionable mail and wakes it for a later turn.

### Conversation Pattern
- The default walkthrough should use one simple repeated question so the conversation remains easy to follow.
- A representative example is: the initiator asks the responder what time it is, the responder replies with the current time, and the initiator asks again.
- The default walkthrough should continue this round-trip conversation for five completed exchanges unless the operator configures a different limit.

### Receiver Behaviour
- When the responder is woken for unread or otherwise actionable mail, it should inspect the relevant message, perform the requested bounded task, and reply in the same thread.
- After successful processing, the responder should update message state in whatever way is appropriate so later wake-up behavior reflects that the message was handled.
- The responder's turn should end after it sends the reply rather than waiting for the initiator's next message.

### Sender Behaviour
- When the initiator is woken by a reply, it should inspect the relevant response, decide whether the conversation should continue, and if so send the next message in the sequence.
- The initiator should stop sending further messages once the configured round limit is reached.
- The initiator's turn should also end immediately after send.

### Gateway Wake-Up Semantics
- Progress after the initial kickoff should depend on the existence of actionable mailbox state plus session eligibility, not on hard-coded immediate chaining between the two agents.
- The demo should make it clear that wake-up behavior is about "mail requires attention" rather than "every delivered message must create one exact prompt event".
- The demo should preserve the idea that gateway wake-up is a later-turn trigger, not a special inline substep inside the sender's current turn.

### Observability
- The demo should let users inspect:
  - which messages were sent,
  - which thread each message belongs to,
  - when each agent was woken,
  - when each turn completed,
  - how the five-round conversation progressed,
  - why the demo is considered successful or incomplete.
- The demo should expose this through stable demo-owned artifacts rather than requiring guesswork from raw terminal text alone.

## Acceptance Criteria
1. The repository contains a demo under `scripts/demo/` that presents a two-agent mailbox ping-pong conversation as a first-class workflow.
2. The demo can run one default end-to-end conversation where the initiator and responder complete five round trips through mailbox messages and later gateway wake-ups.
3. The demo contract supports headless, TUI, and mixed participant pairings without redefining the logical conversation semantics for each pairing.
4. After an agent sends a message, that turn is considered complete without requiring the sender to wait inline for the reply.
5. Later turns are driven by gateway wake-up from mailbox state rather than by manual direct prompting after every single message.
6. The responder can read a simple request from mail, perform the requested bounded action, and send a reply in the same thread.
7. The initiator can read the reply, decide whether the configured round limit has been reached, and either send the next message or stop.
8. The demo exposes enough evidence to reconstruct the sequence of sent messages, replies, wake-ups, and turn completions.
9. The demo README explains this workflow as a canonical Houmao usage pattern for asynchronous agent-to-agent coordination.
10. Choosing headless, TUI, or mixed participants does not require redefining the expected agent behaviour; only the launch and observation surface may vary.

## Non-Goals
- This request does not require one specific backend, mailbox transport, or gateway attachment mechanism.
- This request does not require the example question to be permanently fixed to "what time is it", though a simple repeated question is desirable for clarity.
- This request does not require the demo to define a production-scale multi-agent orchestration framework.
- This request does not require one exact internal artifact schema, queue implementation, or storage layout.
- This request does not require the two-agent demo to prove every possible mailbox or gateway edge case in the same first version.
- This request does not require different semantic rules for headless-only, TUI-only, and mixed-mode runs.

## Suggested Follow-Up
- Create an OpenSpec change for the demo contract and participant-mode matrix.
- Decide the minimal stable artifact set needed to inspect message flow, wake-up flow, and round completion.
- Add reference documentation that points users to this demo when explaining mailbox-backed asynchronous coordination.
