# Runtime Mail Model

## Purpose

MUST READ before clarifying, generating, validating, preparing, starting, recovering, or stopping any mail-driven loop.

Use this page for mail-driven loop semantics, on-event skills, on-tick skills, notifier prompts, and communication defaults.

## Runtime Model

- Houmao agents do not run a conventional always-awake loop inside one chat turn.
- The Houmao email/notifier system runs separately from the target agents.
- When notifier support detects open mail for an agent, it sends that agent a prompt.
- The prompt should guide the agent to:
  - check and process the relevant mail;
  - use the generated mail-received on-event skill for the matching message family when applicable;
  - call any required on-tick skill after mail processing when the generated loop wants follow-up scheduling, reconciliation, timeout, or completion work.
- Mail notification prompts are customizable and may include loop-specific instructions.

## On-Event And On-Tick

- On-event skills are entered from a notifier or operator prompt that presents a concrete event, usually received mail.
- On-event skills handle one bounded role-owned action, then stop.
- On-tick skills are not periodic background loops.
- On-tick skills are invoked from a notifier or operator prompt turn.
- On-tick skills perform one bounded pass, then stop.
- After processing mail and any requested tick, the agent finishes the chat turn and waits for the next notifier or operator prompt.

## Waiting Rule

- Do not design generated agents to sleep, poll, tail logs, or wait in-chat for future work.
- In-chat waiting blocks later mail notification prompts from being handled.
- Do not rely on an external periodic driver to wake agents for ticks.
- Model tick execution as prompt-triggered follow-up work.

## Communication Defaults

- Cross-agent participant communication defaults to Houmao mail unless intention source explicitly requests a non-mail mechanism.
- Do not ask the user to decide whether ordinary participant handoffs should use mail when intention source is silent.
- Clarify loop-specific communication facts:
  - routes;
  - message families;
  - payload fields;
  - reply expectations;
  - state or record effects.
- Generated loop material owns communication semantics:
  - participant routes;
  - message families;
  - structured payload schemas;
  - Markdown render templates;
  - reply expectations;
  - loop-local state or record effects caused by mail.

## Mail Family Defaults

- Participant-to-participant loop mail is templated by default.
- Operator-origin control, override, recovery, stop, resume, or unsupported-instruction mail may remain freeform and high priority.
- Generated mail schemas may use platform mail ids, thread ids, and message refs as opaque identifiers.
- Generated mail renderers should keep structured metadata machine-readable while preserving readable Markdown for humans.
