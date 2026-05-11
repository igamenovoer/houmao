## Context

The packaged loop skill already has a generated execplan communication layer and mentions mail-driven loops, but the guidance is too implicit. A recent usage case needed ADRs for async mail-driven agents, inter-agent mail schema, mail referencing, and delegation to Houmao mail skills. Those are mostly generic defaults for Houmao loop generation, not domain-specific decisions.

A mature reference plan shows a stronger generic pattern: participant-to-participant mail is templated, operator-origin mail remains freeform and high priority, each generated mail family has a template registry entry, payloads share a common envelope, rendered Markdown carries machine-readable metadata plus human-readable sections, and the harness validates/renders/records payload lifecycle while Houmao mail support owns delivery.

The implementation should tighten the packaged skill guidance without changing Houmao mailbox APIs. The skill should still remain domain-neutral and should avoid standalone version-language in the skill body except where the actual skill name appears.

## Goals / Non-Goals

**Goals:**
- Make Houmao mail the default cross-agent communication mechanism for generated loops.
- Make generated execplans responsible for communication semantics: routes, message families, schemas, renderers, reply expectations, and mail-caused state or record effects.
- Make the generated comms package shape concrete enough that agents stop inventing ad hoc mail contracts.
- Default participant-to-participant mail to templated payloads with schema validation, Markdown rendering, and lifecycle records.
- Make maintained Houmao skills responsible for platform mechanics: mailbox administration, ordinary mail actions, gateway-notified rounds, managed-agent messaging, and gateway lifecycle.
- Reduce unnecessary `clarify intent` questions by turning generic mail transport choices into defaults.
- Add validation and test coverage so the packaged skill preserves these defaults.

**Non-Goals:**
- Do not change Houmao mailbox, gateway, or managed-agent APIs.
- Do not introduce a new mail transport or custom mailbox storage.
- Do not make a domain-specific message family set mandatory.
- Do not make a reference plan's exact topology, template names, evidence fields, or state implementation mandatory.
- Do not require every loop to be mail-only; explicit non-mail intentions can still be represented.

## Decisions

### Default Cross-Agent Communication To Houmao Mail

The top-level skill and authoring subskills should state that cross-agent participant coordination defaults to Houmao mail unless the intention explicitly asks for a non-mail mechanism. This prevents clarification from repeatedly asking whether mail should exist at all.

Alternative considered: leave mail as one option among many. That keeps the skill flexible, but it makes every loop authoring session rediscover the same Houmao platform default.

### Separate Communication Semantics From Platform Mechanics

Generated execplans should define what communication means for the loop: message families, sender/recipient roles, payload fields, render templates, expected replies, state or record updates, and whether a tick is needed for aggregation or scheduling. They should not define how mailbox roots are created, how messages are persisted, or how a gateway endpoint is discovered.

Platform mechanics should route to maintained skills:
- `houmao-mailbox-mgr` for mailbox setup, inspection, and administration;
- `houmao-agent-email-comms` for ordinary mail status/list/read/send/reply/archive work;
- `houmao-process-emails-via-gateway` for notifier-driven open-mail rounds when the gateway base URL is provided;
- `houmao-agent-messaging` for managed-agent communication and mailbox handoff routing;
- `houmao-agent-gateway` for gateway lifecycle and gateway posture.

Alternative considered: generate a loop-local mail subsystem. That duplicates Houmao platform behavior and would require every generated loop to maintain transport details.

### Keep Structured Payloads And Human-Readable Mail Together

For generated mail families, the skill should keep the existing pattern: structured payload, schema validation, Markdown rendering, then Houmao mail send or reply. The structured payload gives harness validation and auditability; the rendered Markdown gives agents a human-readable task surface.

The generated contract should not require a single hard-coded serialization detail for every loop beyond the current default of TOML payloads. If a loop has a reason to use another structured format, that should come from intention source.

### Generate A Communication Registry

Mail-driven execplans should generate a `specs/comms/templates.toml` registry that maps each generated mail family to its JSON Schema and Markdown renderer. The registry should support both short template names and full schema ids in harness commands.

The default package shape should include:
- `specs/comms/templates.toml`;
- `specs/comms/schemas/<message-family>.schema.json`;
- `specs/comms/renderers/<message-family>.md.j2`;
- `specs/comms/comms-overview.md` or equivalent generated human support view.

Alternative considered: describe schemas and renderers only in prose. That is easier to generate initially, but it gives agents no stable discovery surface and makes validation weaker.

### Use A Common Payload Envelope

Every templated participant mail payload should have common fields unless the intention source explicitly chooses another convention:
- `schema_id`;
- `schema_version`;
- `payload_id`;
- `kind`, normally `request`, `reply`, `notice`, or `ack`;
- `run_id`;
- `plan_revision`;
- `handoff_id` or another generated exchange id;
- `context`.

Request payloads should normally include `requested_reply_schema_id` when a reply is expected. This makes request/reply pairing explicit and gives receiver skills a concrete target for outgoing payload construction.

### Use A Standard Rendered Markdown Shape

Rendered generated mail should carry a machine-readable metadata block, then human-readable sections. The default rendered shape is:
- fenced `houmao-email-metadata` containing schema id, schema version, kind, run id, plan revision, exchange or handoff id, and important routing/result refs;
- `Context`, required in every rendered template;
- template-specific sections for request, reply, directive, result, notice, evidence, or other loop-specific content;
- explicit `Reply Request` when the sender expects a reply.

This keeps the rendered message useful to agents while preserving enough structured metadata for routing and audit.

### Track Payload Lifecycle Without Owning Mail Delivery

The harness should support email commands for `schema`, `validate`, `render`, and, when runtime state exists, `apply` and `query`. `apply` records payload lifecycle facts such as `payload_id`, `schema_id`, `kind`, exchange id, source payload, status, platform `message_id`, failure reason, and timestamps.

The harness should not send mail. Mailbox delivery, reply, read, and archive remain owned by maintained Houmao mail support. This boundary lets generated loops keep compact auditable facts while the mailbox remains the source for delivered human-readable content.

### Provide Generic Built-In Notice Families

Generated mail-driven loops should include generic `freeform-notice` and `ack` families by default unless the intention source forbids them. `freeform-notice` covers operator or participant instructions that do not fit a task-specific request/reply template but still benefit from validation. `ack` covers receipt acknowledgement without changing loop state.

### Generate Mail-Received Event Skills

Mail-driven loops should usually produce on-event skills named around received message families, such as `<role>-on-<message-family>-received`. These skills should handle one bounded mail event: inspect selected mail, validate structured payload through the harness when needed, perform the role-owned action, send any required reply through Houmao mail support, archive processed mail only after required work and replies succeed, and then stop.

Tick skills remain separate. They are for aggregation, scheduling, reconciliation, completion checks, or “what now?” decisions that do not belong to one received mail.

### Avoid Custom Prompt-Injected Mail History

Generated loop guidance should treat Houmao `message_ref` and `thread_ref` values as opaque platform references. It should not ask users to design custom message IDs, custom mailbox read/unread state, or full-mail prompt injection unless the intention explicitly requires a custom non-Houmao transport.

## Risks / Trade-offs

- [Risk] The defaults could feel too opinionated for non-mail loop designs. → Mitigation: Phrase mail as the default for cross-agent participant coordination, with explicit non-mail intention allowed.
- [Risk] Generated execplans may over-reference platform skill names. → Mitigation: Keep platform mechanics delegated by name, but put loop-specific communication semantics under generated `specs/comms/`, `skills/`, `agents/`, and `harness/`.
- [Risk] Agents may still ask generic mail questions during clarification. → Mitigation: Add explicit clarify guidance and targeted tests for “do not ask whether to use mail by default” behavior.
- [Risk] Mail rendering/schema language could drift from maintained mail skill APIs. → Mitigation: Do not duplicate endpoint contracts in the loop skill; refer to maintained Houmao mail skills for actual send/read/reply/archive operations.
- [Risk] The generated comms package could overfit to the reference plan. → Mitigation: Extract only generic package shape, payload envelope, registry, rendered-mail sections, lifecycle state, and event-skill boundaries; leave topology, template families, and domain fields to intention source.
