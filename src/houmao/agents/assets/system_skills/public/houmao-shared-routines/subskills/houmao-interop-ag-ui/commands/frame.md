# Frame Standard AG-UI Event Batches

## Workflow

1. **Validate the rendered event batch first** via `houmao-mgr ag-ui protocol events validate --input events.json`.
2. **Select the target wire format** (`json`, `jsonl`, or `sse`) required by the consumer or third-party endpoint.
3. **Frame the batch** via `houmao-mgr ag-ui protocol events frame --input events.json --format <json|jsonl|sse>`.
4. **Deliver or return the framed output**: for a Houmao gateway use [publish.md](publish.md) instead of custom HTTP; for a third-party AG-UI endpoint, follow only the endpoint-specific URL, auth, and transport instructions supplied by the user.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/protocol-and-impl.md](../references/protocol-and-impl.md) and the user request, then execute the plan.

## Guardrails

- DO NOT assume a third-party AG-UI endpoint accepts Houmao gateway route fields, auth headers, content types, or stream semantics.
- DO NOT invent third-party endpoint URLs, headers, credentials, or route IDs.
