# Publish AG-UI Events to a Live Houmao Gateway

## Workflow

1. **Verify the input is a validated standard AG-UI event batch** (`houmao-mgr ag-ui protocol events validate --input events.json`), never a raw implementation payload.
2. **Select the scoped gateway command** matching the actor frame:
   - Verified self (`agent` posture): `houmao-mgr agents self gateway ag-ui publish --input events.json`
   - Explicit target (`admin` or peer): `houmao-mgr agents single --agent-id <id> gateway ag-ui publish --input events.json` (or `--agent-name <name>`)
3. **Apply routing flags conservatively**: omit routing flags when relying on gateway destination resolution (explicit request/batch destination -> gateway `active-thread` -> internal default sink); pass `--thread-id <id>` only when known, and pass `--run-id` or `--connection-id` only for a known active run or GUI connection.
4. **Inspect the response fields** (`accepted_count`, `stored_count`, `delivered_count`, `warnings`) and report delivery honestly per **Fanout Interpretation** below.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/protocol-and-impl.md](../references/protocol-and-impl.md) and the user request, then execute the plan.

## Fanout Interpretation

- **Live-only fanout**: `stored_count` is normally `0`; the gateway does not buffer missed GUI events for later replay.
- **`delivered_count > 0`**: matching live GUI or run streams received the batch immediately.
- **`default_sink_due_to_no_destination` warning or `delivered_count == 0`**: the gateway accepted the events (`accepted_count`), routed them to the internal sink or found no matching live subscriber, and did not display them in the GUI. Ask the user to connect the workbench or mark the target pane `active-thread`, then republish.
- **Bookkeeping note**: `last-sent-thread` is diagnostic history only and is never used as an automatic routing fallback.

## Guardrails

- DO NOT pass `--endpoint` to `gateway ag-ui publish` (none exists; third-party endpoints use [frame.md](frame.md) plus their own transport).
- DO NOT invent sink thread IDs or guess `--run-id` / `--connection-id` (a wrong `--run-id` narrows delivery to `delivered_count: 0`).
- DO NOT claim the GUI rendered an event batch unless `delivered_count > 0` or the user confirms external receipt.
