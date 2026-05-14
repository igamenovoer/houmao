## Why

The general loop skill currently mentions mail-driven loops and structured payload rendering, but it does not make Houmao mail the default cross-agent communication model or clearly separate generated loop semantics from Houmao platform mail mechanics. In usage, that ambiguity causes clarify sessions to ask repeated foundational questions about whether to use mail, how mail is delivered, how mail is referenced, and which Houmao skills own mailbox behavior.

## What Changes

- Add explicit loop communication defaults to the packaged loop skill: cross-agent participant coordination defaults to Houmao mail unless the intention explicitly asks for a non-mail mechanism.
- Clarify that generated loop material owns semantic communication contracts such as participant routes, message families, payload schemas, render templates, reply expectations, and mail-caused state or record updates.
- Define the default generated mail contract package shape: `specs/comms/templates.toml`, `specs/comms/schemas/*.schema.json`, `specs/comms/renderers/*.md.j2`, harness email commands, and schema-id-triggered mail-received skills.
- Establish default templated participant mail conventions: common payload envelope, metadata-bearing rendered Markdown, request-to-reply schema links, payload lifecycle records, and default `freeform-notice` / `ack` families.
- Clarify that maintained Houmao skills own transport and platform mechanics: mailbox administration, ordinary mail send/read/reply/archive, gateway-notified open-mail rounds, managed-agent messaging, and gateway lifecycle.
- Tighten clarify guidance so agents do not ask whether to use mail or custom mail transport by default; they should ask loop-specific questions about message families, payload fields, routing, reply behavior, aggregation, and tick responsibilities.
- Tighten execplan generation and validation guidance so mail-driven loops generate schema/render communication contracts and mail-received event skills that route actual mailbox operations through maintained Houmao mail skills.
- Update developer design notes and targeted tests to preserve these defaults.

## Capabilities

### New Capabilities
- `loop-mail-communication-defaults`: Default communication behavior for generated loop plans, including Houmao mail routing, generated message-family contracts, mail-received event skills, and delegation to maintained Houmao mail support.

### Modified Capabilities

None.

## Impact

- Affected packaged assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`.
- Affected supporting specs/tests: system-skill unit tests that assert packaged skill guidance.
- Affected runtime behavior indirectly: generated loop execplans should become less ambiguous about mail, but maintained Houmao mail APIs and platform skills are not changed by this proposal.
