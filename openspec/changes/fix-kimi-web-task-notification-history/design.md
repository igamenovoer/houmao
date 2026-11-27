# Design

## Context

### Contract Review

| Boundary | Existing contract | Finding |
| --- | --- | --- |
| Kimi → Houmao | Kimi represents prompt IDs as strings. Its task service constructs `task:<taskId>:<status>`. The native prompt API accepts nonempty strings. | A colon-bearing task ID is legitimate provider data. Kimi emitted one in the verified session’s journal. |
| Kimi Web adapter → gateway | `kimi-web-control` requires exact prompt identity, passive observation of native activity, and exact-target interruption. Managed ownership requires correlation with a specific request. | The contract already requires correct observation. It leaves the distinction between a native prompt ID, an owned request ID, and an HTTP path segment implicit. The adapter conflates those identities. |
| Gateway → CCCC | A gateway needs fresh, reconciled native state before admitting input. CCCC keeps unstarted work pending until the same recipient can accept it. | Refusing admission followed the existing contract after the adapter failed. A healthy binding alone cannot establish native readiness. |

The local Kimi source reference is at revision `67325c1`. Its task ID constructor, prompt schema, and client-side abort route establish what Houmao consumes and how Kimi addresses it. The archived Houmao design explains why the gateway correlates managed work to an exact bound prompt. [Kimi task service](../../../extern/orphan/kimi-code/packages/agent-core-v2/src/agent/task/taskService.ts) · [Kimi prompt schema](../../../extern/orphan/kimi-code/packages/kap-server/src/protocol/rest-prompt.ts) · [Kimi HTTP client example](../../../extern/orphan/kimi-code/packages/klient/test/e2e/harness/http.ts) · [Original Houmao design](../archive/2026-11-19-run-modes-07-add-kimi-web-mode/design.md) · [CCCC chat contract](../../specs/cccc-chat/spec.md)

### Root Cause and Classification

1. **Reproduced implementation bug.** At 20:20:03.241 UTC, after A’s original turn ended, Kimi 2.8.0 wrote a task-origin `turn.prompt` with ID `task:bash-83zor4x4:completed`. `KimiWebSession._history_entries()` passed it to `native_id()`, whose path-component pattern excludes colons. Both `observe_web_state()` and `observe_web_history()` use this projection. The shared observer converts the exception into unavailable state and closes admission. Subsequent refreshes encounter the same row. [Adapter](../../../src/houmao/agents/realm_controller/backends/kimi_web.py) · [Validator](../../../src/houmao/agents/realm_controller/backends/kimi_web_client.py) · [Gateway observer](../../../src/houmao/agents/realm_controller/web_observation.py)
2. **Adapter contract defect.** A single validation rule currently serves observed native prompt IDs, session/host identity, and the prompt target of an HTTP action. An ID can be valid as an opaque correlation value yet require encoding on the wire. The interrupt path uses the same rule. This second call site is a code finding; the live failure occurred during observation. The shared gateway model already carries string message IDs and event cursors. The evidence places the correction inside the Kimi adapter.
3. **Independent timing condition.** The 300-second wait expired while A’s managed turn was still running. Its native terminal record and subsequent settlement appear about 6 minutes 49 seconds after kickoff. The journal reader fails offline without any wait, CCCC process, or GPU. The separate B-to-C receipt recorded `dispatch_failed` with an uncertain outcome. C’s retained journal projects successfully; its dispatch failure has no established causal link to A's exception.

The differential replay on run `20261127T201107Z-dRSNNPzf` projected 12 transitions before A’s notification, raised `identity_mismatch` upon including it, and projected 13 transitions when records with that prompt ID were excluded. B, C, and D’s complete journals yielded 45, 54, and 54 transitions. The final queue sample contained 16 messages for A. These measurements isolate the trigger. The fixture proposed below exercises the repair using synthetic records suitable for CI. [Run report](../../../.imsight-arts/project-mgr/agent-driven-testing/reports/20261127T201107Z-dRSNNPzf.md) · [Local replay evidence](../../../tmp/cuda-coop/20261127T201107Z-dRSNNPzf/evidence/agent-cccc-cuda-coop/four-agent-cuda-coop/journal-projection-check.json)

## Goals / Non-Goals

The goal is a consistent native prompt identity across reads, comparisons, and exact-target control. Scope is the Kimi Web adapter. The existing contracts continue to govern listener ownership, journal continuity, busy-session delivery, and timeout recovery. A redesign of generic gateway diagnostics or CCCC retry policy would require separate evidence.

## Decisions

| Use of an identifier | Responsible boundary | Proposed handling |
| --- | --- | --- |
| Read a native prompt ID from the verified journal | Kimi history projection | Preserve the provider's nonempty string exactly for metadata and equality. Record the existing start, end, and settlement transitions at the same byte offsets. Preserve event-specific handling for records that omit a prompt ID, such as `turn.ended`. |
| Settle a Houmao-managed operation | Managed attempt and native closure | Continue to require the saved execution identity, journal continuity, exact prompt ID, and attributable terminal evidence. A native task can finish independently while the managed outcome remains uncertain. |
| Address an active prompt for interruption | Kimi HTTP adapter | Recheck the captured binding, turn-start offset, and optional managed operation. Serialize the original prompt ID as one percent-encoded path segment at the HTTP boundary, then append the literal `:abort` action. Preserve the provider's actual response if the target has already finished. |
| Select a native host, session, or persisted workspace journal | Kimi binding and client | Retain the strict component validation and exact-owner checks that protect these lookups. An ID read from a journal supplies no authority to select a host, session, or file. |

An allowlist entry for `task:` would encode one producer’s spelling in the consumer. Widening the common validator would apply prompt syntax to host and session identifiers. Dropping the notification row would hide a real active turn and its capture point. Keeping each rule at its owning boundary covers valid native producers and uses the gateway’s existing readiness machinery.

## Risks / Trade-offs

- **Wrong prompt receives an interrupt.** Keep the original ID for equality and encode once when constructing the request. Cover punctuation that changes its wire spelling, literal percent sequences, stale turns, and mismatched managed operations.
- **A recovered observer reports readiness too early.** Exercise the public state and incremental-history reads while the native notification is active and again after completion. Keep actual native activity, pending interactions, and the final pre-send check authoritative.
- **A green parser test masks a delivery problem.** In a focused live acceptance check, stage one message to a busy Kimi recipient. Require an accepted receipt and exactly one matching native input on the same binding after idle. A second independent failure stays visible in its own evidence.

## Migration Plan

Ship the adapter correction through the normal Houmao release. Existing journals already contain the original IDs and can be read in place. Verify the patched reader against a synthetic journal containing prior activity and, when available locally, the retained run. A rollback restores the previous reader and can therefore reproduce the issue on an affected journal.
