# Mail Schema Events

## Purpose

Use this page when generating mail-driven communication contracts, renderers, harness commands, on-event skills, or notifier prompts.

## Schema Id As Mail Type

Generated templated participant mail uses `schema_id` as the loop-local mail type.

Default package shape:

```text
execplan/specs/comms/
  templates.toml
  schemas/<message-family>.schema.json
  renderers/<message-family>.md.j2
```

`templates.toml` maps:
- template name;
- `schema_id`;
- JSON Schema path;
- Markdown renderer path.

## Authoring Flow

Outgoing templated mail uses:

```text
TOML payload -> JSON Schema validation -> Markdown rendering -> Houmao mail delivery
```

The harness may expose commands such as:
- `email schema`;
- `email validate`;
- `email render`;
- `email apply`;
- `email query`.

`apply` records lifecycle or bookkeeping state when generated contracts need it. It is not mailbox delivery.

## In-Body Metadata Header

Rendered templated mail starts with a parseable in-body header, normally:

````text
```houmao-email-metadata
schema_id = "<loop-slug>.email.<message-family>"
schema_version = "1"
kind = "request"
run_id = "<run-id>"
plan_revision = "<plan-revision>"
payload_id = "<payload-id>"
handoff_id = "<handoff-or-exchange-id>"
```
````

Add route, reply, result, work-item, or participant identifiers when the generated mail family needs them.

## On-Event Dispatch

Generated on-event mail skills state their trigger by exact `schema_id`.

Notifier prompts and agent bindings should tell agents to:
- inspect the in-body metadata header;
- select the matching generated on-event skill by `schema_id`;
- process one bounded event;
- archive only after successful processing when generated or maintained mail policy requires it.

## Boundaries

- Sender owns outgoing payload validation before render/send.
- Receiver skills may assume ordinary templated mail is well formed and inspect it semantically.
- Freeform, operator-origin, malformed, or unknown-schema mail uses explicit fallback or repair paths when the loop needs them.
- Do not rely only on subject text, sender identity, or hidden transport headers for event dispatch.
