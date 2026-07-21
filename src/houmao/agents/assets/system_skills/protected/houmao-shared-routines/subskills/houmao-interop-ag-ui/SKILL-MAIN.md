---
name: houmao-interop-ag-ui
description: "Use Houmao AG-UI interop helpers for standard AG-UI event validation, event framing, generic tool-call rendering, Houmao implementation validation/rendering, and Houmao gateway publishing. Use when Codex needs to validate, frame, render, publish, route, or interpret AG-UI event batches for already-chosen Houmao implementation payloads, tables, metric grids, dashboards, or frontend-specific GUI messages."
skill_invocation_notation: >
  Top-level skill entrypoints use SKILL.md. Parent-scoped subskill entrypoints use
  SKILL-MAIN.md and are loaded explicitly through their parent; nested SKILL.md is
  accepted only as legacy input when SKILL-MAIN.md is absent.
  Skill and subskill entrypoints use bare object paths: `X` invokes skill X and
  `X->Y->Z` invokes subskill Z. Subcommands use parenthesized components:
  `X->cmd()` invokes a direct subcommand, `X->Y->cmd()` invokes a subcommand of
  subskill Y, and `X->parent()->child()` invokes child subcommand child exposed
  by parent subcommand parent. Intermediate subcommands act as object generators.
  Forms such as `X()` and `X->Y()` are invalid for skill or subskill entrypoints.
---

# Houmao Interop AG-UI

## Actor Frame Gate

This protected routine MUST NOT execute standalone. Require an immutable admin or verified-agent frame from the containing public entrypoint. Keep gateway and delivery targets explicit in the admin branch; use freshly verified self gateway context by default in the agent branch. Missing or mismatched frames fail closed.

Use maintained Houmao tooling to render, validate, and deliver AG-UI event batches.

Typed Houmao implementations are application-layer contracts carried inside standard AG-UI tool-call events. The gateway validates standard AG-UI event shape and routing only. `houmao-mgr ag-ui protocol` owns schema-agnostic AG-UI event validation and framing. `houmao-mgr ag-ui impl` owns Houmao implementation schema discovery, payload validation, and event generation.

## Help

When the user asks `$<public-entrypoint> interop-ag-ui help`, `help for houmao-interop-ag-ui`, or what this skill can do, answer from this section and stop unless they also ask for a concrete AG-UI action. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me publish these events to the GUI", route to the matching workflow instead of stopping at generic help.

Purpose: work with standard AG-UI event batches without hand-writing raw event JSON or guessing gateway delivery details.

Available functionality:

- Validate standard AG-UI event batches.
- Frame standard AG-UI event batches as JSON, JSON Lines, or SSE.
- Render schema-agnostic custom tool calls for frontend-specific components.
- List Houmao AG-UI implementation schemas.
- Show one implementation schema and example.
- Validate an already-authored Houmao implementation payload.
- Render a valid implementation payload into standard AG-UI events.
- Publish a rendered event batch to the live Houmao gateway for the current or selected agent.
- Interpret gateway publish responses accurately.

Common starting prompts:

- `$<public-entrypoint> interop-ag-ui help`
- `$<public-entrypoint> interop-ag-ui validate these AG-UI events`
- `$<public-entrypoint> interop-ag-ui render a custom frontend tool call`
- `$<public-entrypoint> interop-ag-ui publish these events to my GUI`

Related skills and boundaries:

- Use `<public-entrypoint>->houmao-shared-routines->agent-gateway` for gateway lifecycle, attachment, status, reminders, and direct gateway controls.
- Use `<public-entrypoint>->houmao-shared-routines->agent-messaging` for prompts, interrupts, and live managed-agent communication.
- Use this skill only for AG-UI protocol, implementation rendering for already-chosen payloads, event delivery, and delivery interpretation workflows.
- Do not use this skill to submit ordinary prompt work.

## Launcher

Choose one `houmao-mgr` launcher for the turn:

1. Run `command -v houmao-mgr` and use the command on `PATH` when present.
2. If that fails, use `uv tool run --from houmao houmao-mgr`.
3. For repo development only, use the project launcher such as `pixi run houmao-mgr`.
4. If the user names a launcher, use that launcher.

Reuse the same launcher for discovery, validation, rendering, and publishing in the same turn.

## Protocol and Implementation Split

- Standard AG-UI protocol: standard event arrays such as `TOOL_CALL_START`, `TOOL_CALL_ARGS`, and `TOOL_CALL_END`. Use `houmao-mgr ag-ui protocol ...` for schema-agnostic validation, framing, and generic tool-call rendering.
- Houmao AG-UI impl: Houmao-owned implementation contracts such as `houmao.table`, `houmao.metric_grid`, and `houmao.dashboard`. Use `houmao-mgr ag-ui impl ...` for schema discovery, payload validation, rendering, and catalogs when the implementation has already been chosen.
- Custom frontend components: use `houmao-mgr ag-ui impl new-component render` only when the user supplies or confirms the GUI-side implementation contract.
- Houmao gateway publishing: use `houmao-mgr agents ... gateway ag-ui publish`.
- Third-party endpoints: use `houmao-mgr` only to generate, frame, or validate events, then deliver the generated event batch with endpoint-specific instructions from that endpoint.

Do not ask the gateway to validate Houmao implementation semantics. Protocol validation only means the event shape is standard AG-UI; it does not prove a GUI can render a custom implementation payload. Do not assume that another AG-UI endpoint accepts Houmao gateway route fields, auth, content type, or stream semantics.

Agent identity is the durable address. A gateway host and port are live transport coordinates that can disappear or change when the agent or gateway restarts. The Houmao workbench stores the selected `agent_id` or unambiguous `agent_name`, resolves the current gateway through the passive server, and reconnects when a matching gateway appears. Do not tell a user that a copied gateway URL is the stable identity of an agent.

The Houmao gateway publishes GUI events as live-only fanout. It does not store missed published events for later replay. The workbench can keep graphics visible only when it was already watching the target and cached the events in the browser.

## Protocol Events

Validate an already-rendered event batch:

```bash
houmao-mgr ag-ui protocol events validate --input events.json
```

Frame an event batch for another endpoint or stream format:

```bash
houmao-mgr ag-ui protocol events frame --input events.json --format json
houmao-mgr ag-ui protocol events frame --input events.json --format jsonl
houmao-mgr ag-ui protocol events frame --input events.json --format sse
```

Render a schema-agnostic standard tool-call event sequence:

```bash
houmao-mgr ag-ui protocol tool-call render --tool-name myapp.graphic.timeline --args payload.json > events.json
houmao-mgr ag-ui protocol events validate --input events.json
```

Protocol validity does not imply render support. Only a GUI that implements the matching tool-call contract can render the payload.

## Houmao Implementations

List supported Houmao implementations:

```bash
houmao-mgr ag-ui impl list
```

Show a schema and example:

```bash
houmao-mgr ag-ui impl schema houmao.table
houmao-mgr ag-ui impl schema houmao.metric_grid
houmao-mgr ag-ui impl schema houmao.dashboard
```

Validate an already-authored implementation payload:

```bash
houmao-mgr ag-ui impl validate houmao.table --input payload.json
```

Render a valid implementation payload into standard AG-UI events:

```bash
houmao-mgr ag-ui impl render houmao.table --input payload.json > events.json
```

Supported render formats:

```bash
houmao-mgr ag-ui impl render houmao.table --input payload.json --format json
houmao-mgr ag-ui impl render houmao.table --input payload.json --format jsonl
houmao-mgr ag-ui impl render houmao.table --input payload.json --format sse
```

Render a frontend-specific tool call when the user has supplied the GUI-side implementation contract:

```bash
houmao-mgr ag-ui impl new-component render --tool-name myapp.graphic.timeline --args payload.json > events.json
houmao-mgr ag-ui protocol events validate --input events.json
```

Do not require frontend-specific tool names to appear in `houmao-mgr ag-ui impl list`. Houmao implementation commands add schema discovery and payload validation only for Houmao-known implementations.

## Publish to Houmao Gateway

Publish only to the Houmao gateway through the scoped gateway command family.

Current agent:

```bash
houmao-mgr agents self gateway ag-ui publish --input events.json
```

Selected agent:

```bash
houmao-mgr agents single --agent-id <agent-id> gateway ag-ui publish --input events.json
houmao-mgr agents single --agent-name <agent-name> gateway ag-ui publish --input events.json
```

For the Houmao AG-UI workbench, a tmux-controlled agent often lacks GUI-appended canvas or thread context. In that case, omit explicit routing and let the gateway resolve the destination. The gateway order is:

1. Destination specified in the publish request or rendered event batch.
2. Gateway `active-thread`, set by the workbench active-thread control or by an eligible pane connect action.
3. Houmao default sink.

The default sink is gateway-defined and is not an agent-visible thread name. Do not invent or target a sink thread id.

Gateway `last-sent-thread` is bookkeeping only. It records the last concrete non-sink publish destination, but the gateway does not use it as fallback routing when a later publish omits routing.

Use `--thread-id <thread-id>` by itself when the user or environment gives a known destination thread. A pane-level connect stream and an active run stream both receive thread-only publishes for the same thread. Adding `--run-id` narrows delivery to a stream with that exact run id, so a guessed, newly generated, stale, or copied-but-wrong run id will usually produce `delivered_count: 0` and the GUI will render nothing.

Use `--run-id` only when targeting one known active run stream. Use `--connection-id` only when targeting one known active GUI connection. Do not guess routing ids. If no routing id is known, ask for it or inspect the current GUI connection state through maintained gateway surfaces.

Check the publish response:

- `accepted_count` is the number of standard AG-UI events accepted by the gateway after validation.
- `stored_count` is normally `0` for Houmao gateway GUI-event publish because the gateway does not retain missed events for replay.
- `delivered_count` is the number of live stream deliveries made immediately.
- `warnings` may include `default_sink_due_to_no_destination` when the gateway accepted the batch but had no message-specified or active-thread destination.

`delivered_count > 0` means matching live GUI/run streams received the events immediately. `delivered_count: 0` with `stored_count: 0` means no matching live stream received the events and the Houmao gateway did not retain them for later replay. Do not describe a publish as visible in the GUI unless `delivered_count > 0` or the user confirms that the GUI received it through another path.

If the response warns `default_sink_due_to_no_destination`, report that the gateway accepted the events but sent them to the internal default sink because no GUI destination was available. Do not claim that the GUI displayed the message.

If the user expected a visual message to appear but `delivered_count` is zero, ask the user to open or watch the intended workbench target, mark the pane active when relying on omitted routing, and publish the event batch again after a listener is connected.

This command intentionally has no `--endpoint` option. For third-party endpoints, generate, frame, or validate the event batch with `houmao-mgr ag-ui ...`, then use that endpoint's documented delivery method.

## Example: Table Payload

```json
{
  "schemaVersion": 1,
  "title": "Top Issues",
  "columns": [
    { "key": "id", "label": "ID" },
    { "key": "count", "label": "Count", "kind": "number", "align": "right" }
  ],
  "rows": [
    { "id": "A", "count": 4 },
    { "id": "B", "count": 2 }
  ]
}
```

Render and publish:

```bash
houmao-mgr ag-ui impl validate houmao.table --input payload.json
houmao-mgr ag-ui impl render houmao.table --input payload.json > events.json
houmao-mgr ag-ui protocol events validate --input events.json
houmao-mgr agents self gateway ag-ui publish --input events.json
```

After publishing, report the response accurately. If `delivered_count > 0`, say the gateway delivered the batch to live stream subscribers. If the response includes `default_sink_due_to_no_destination`, say that no GUI destination was available and the gateway used the internal sink. If `delivered_count` is zero without that warning, say only that the gateway accepted the batch and no live GUI stream received it.

## Safety

- Do not include credentials, tokens, cookies, private key material, or unredacted auth files in payloads or events.
- Do not include private local file contents unless the user explicitly asks to display that exact content.
- Do not use raw unsanitized HTML, scriptable SVG, JavaScript URLs, iframe content, or event-handler attributes.
- Prefer typed fields such as labels, numeric values, rows, metrics, dashboard children, and rendered standard AG-UI events.
- If validation fails, fix the payload or event batch and rerun validation before rendering or publishing.

## Guardrails

- Do not hand-write AG-UI tool-call event arrays when `ag-ui impl render`, `ag-ui impl new-component render`, or `ag-ui protocol tool-call render` can generate them.
- Do not publish raw implementation payloads directly to the gateway; render them into events first.
- Do not call generic gateway prompt commands to display GUI events. AG-UI publish is separate from prompt admission.
- Do not invent third-party endpoint URLs, headers, auth, route ids, or stream formats.
