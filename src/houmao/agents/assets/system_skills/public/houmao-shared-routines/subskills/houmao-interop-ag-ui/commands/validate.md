# Validate AG-UI Events or Implementation Payloads

## Workflow

1. **Determine the artifact layer** using [../references/protocol-and-impl.md](../references/protocol-and-impl.md): standard AG-UI event array (`ag-ui protocol`) vs Houmao implementation payload (`ag-ui impl`).
2. **Inspect the implementation schema when needed** via `houmao-mgr ag-ui impl list` and `houmao-mgr ag-ui impl schema <impl-name>` (for example `houmao.table`, `houmao.metric_grid`, `houmao.dashboard`).
3. **Run the matching validator**:
   - Standard AG-UI event batch: `houmao-mgr ag-ui protocol events validate --input events.json`
   - Houmao implementation payload: `houmao-mgr ag-ui impl validate <impl-name> --input payload.json`
4. **Repair and re-validate on failure** before framing, rendering, or publishing, and state clearly whether protocol shape only or Houmao implementation semantics were validated.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from [../references/protocol-and-impl.md](../references/protocol-and-impl.md) and the user request, then execute the plan.

## Validation Notes

- `ag-ui protocol events validate` verifies standard AG-UI event shape (`TOOL_CALL_START`, `TOOL_CALL_ARGS`, `TOOL_CALL_END`, etc.) only; it does not prove that a target GUI implements a custom tool-call contract.
- Frontend-specific custom tool names (`new-component`) do not appear in `ag-ui impl list` and use `ag-ui protocol events validate` after rendering.

## Guardrails

- DO NOT ask the gateway to validate Houmao implementation payload semantics or proceed to `frame`/`publish` with an invalid batch.
