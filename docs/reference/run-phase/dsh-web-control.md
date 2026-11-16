# DSH Web Native Control

This contract extends the qualified [DSH Web baseline](dsh-web.md). Houmao controls one native conversation in a host it launched. Browser navigation does not change that binding. The supervisory terminal remains a process and log surface.

## Private Connections

`DshWebClient.from_connection(origin, launch_token=..., cookie_file=...)` exchanges the privately supplied native launch token at `/connect` with `interactions=none`. It owns a separate API cookie and WebSocket at `/api/remote.mux`. Browser sign-in independently exchanges the native token at the root page. The API connection does not answer browser questions or approvals.

Closing an API socket revokes its Peer and cookie without stopping the browser or host. An explicit verified reconnection creates another independent Peer. Connection recovery never retries an earlier mutation. The client accepts an explicit loopback HTTP origin, disables ambient HTTP proxy configuration, and follows no HTTP redirects. Credentials and native sign-in URLs remain in private files; public metadata carries the clean origin and native session identity.

The tested rc.3 package exposes its sign-in URL through `ctx.connection.authenticatedUrl(origin)`. Its native service layout differs from the pinned source's separate token-authentication plugin. Controlled tests qualify the actual packaged service against the recorded executable/package identities; they do not attest that npm metadata identifies a source commit.

## Managed Operations

The packaged `managed-web.mjs` companion registers `/houmao/managed/v1/` through the native WebServer and Connection admission path. Every operation requires a live owner Peer. Requests use the native `client-request`/`server-response` envelope and protocol version 1. Native request cancellation and Peer revocation are checked independently.

| Client Method | Native Operation | Behavior |
| --- | --- | --- |
| `describe()` | `describe` | Read protocol and capability metadata without activation |
| `lifecycle_start(mode=..., session_id=...)` | `start` | Explicitly create a new root or restore an exact root after reconciliation |
| `state(identity)` | `state` | Read a fresh native execution, inbox, interaction and model snapshot |
| `history(identity, after_sequence=..., limit=...)` | `history` | Read bounded metadata for the current execution identity |
| `conversation(identity, after_native_sequence=..., limit=...)` | `conversation` | Read allowlisted committed assistant, tool and configuration events from the bound native journal |
| `prompt(identity, text, operation_id=..., deadline_epoch_ms=...)` | `prompt` | Attempt one conditional native inbox insertion |
| `receipt(identity, operation_id)` | `receipt` | Inspect existing metadata without submitting text |
| `interrupt(identity, turn_start_seq=..., operation_id=...)` | `interrupt` | Cancel the captured turn or remove only that operation's unclaimed input |
| `lifecycle_reset(identity)` | `reset` | Claim true idle and an empty, unblocked inbox before replacing the conversation |
| `set_model(identity, provider=..., model=..., reasoning_effort=...)` | `set_model` | Apply an explicit operator model selection after native catalog/configuration resolution |
| `stop(identity)` | `stop` | Dispose the exact native Agent owned by this companion |

Execution identity includes the logical agent, runtime session, managed generation, host incarnation, exact native session, and Agent incarnation. Reusing a native session ID after disposal does not reuse its Agent incarnation. Status and ordinary prompt operations use the existing live registry entry and never activate a cold session. Native `session/create` is a blank-reuse API, so exact restoration uses the explicit lifecycle resume boundary instead.

Explicit lifecycle setup mounts the native Agent preset before publication and installs the native model-selection hook. Exact restore uses the recorded preset and model selection. Ordinary prompts and observation never reapply birth-time model choices. An operator model change follows the native next-step and compaction semantics; incompatible context/output/headroom settings can refuse the later request while preserving the prior request model.

## Admission and Explicit Queues

Native public `status=idle` also covers maintenance. Ordinary delivery therefore prepares content first, then claims `runMaintenance`, which synchronously rejects any active driver or maintenance task. Inside that claim, the companion checks the deadline, caller and Peer lifetimes, execution identity, lifecycle gate, native pending interactions and both inbox placements. It inserts identified input and records admission metadata without an intervening asynchronous boundary.

| Policy | Preconditions | Insertion |
| --- | --- | --- |
| `ready_only` | Exact live execution, true idle, no interaction wait, empty inbox | One ordinary next-turn input |
| `if_no_pending` | Exact live execution, no interaction wait, empty inbox | Explicit operator next-turn queueing, including during active work |
| `always` | Exact live execution and available lifecycle ownership | Explicit operator next-turn queueing despite active or pending work |

Non-default policies require an explicit operator request. Gateway plugin events and mailbox notifications retain ordinary ready-only admission. A refused attempt creates neither a native deferred input nor a gateway delivery retry. Winning programmatic admission does not prevent later native browser queueing, steering or cancellation.

Reset uses its own native true-idle claim. Busy work, maintenance, pending input or an interaction wait refuses reset before the current binding changes. Successful reset retains the host, changes the native conversation and Agent incarnation, and leaves the prior conversation's history available. The runtime must persist the returned identity before sending a prompt to the fresh conversation.

## Receipts, Outcomes and Interruption

An admission receipt identifies an operation and native message. Its state may progress from prepared to admitted, claimed and terminal. Native claims establish the associated turn numbers and sequence evidence. An admitted receipt acknowledges insertion; it does not establish successful execution. Duplicate operation IDs return the original receipt and never insert the supplied text again.

Receipt and companion-history files retain identity, input IDs, policies, sequence boundaries and outcomes. They retain no executable prompt payload. Native journals remain the source for model requests and usage. Human input has its own native identity, and shared-turn claims do not imply an invented token split by sender.

`conversation` is a separate observation surface for committed semantic content. Its exclusive input cursor and inclusive returned cursor track native sequence positions. The cursor advances across filtered rows, and `has_more` indicates another bounded scan. Responses omit native request headers, raw provider streams, provider replay metadata, system instructions and user prompt text. Assistant text/reasoning, tool calls/results, safe lifecycle boundaries and named model/permission settings retain their actual native identities.

Operator interruption captures the current turn's start sequence and execution identity. A different active turn or Agent incarnation refuses cancellation. Attempt-scoped abandonment first removes that operation's still-pending native input. It cancels active work only when native claim evidence associates the operation with the captured current turn. Native cancellation preserves other pending inbox work, which remains visible in state.

## Failure and Explicit Recovery

A lost mutation response is uncertain. Inspect `receipt` and native history through a verified connection; do not submit the text again. An expired deadline, lost caller or revoked Peer during content preparation is rechecked before insertion. Host or Agent replacement invalidates captured dispatch authority.

Exact recovery reconciles abandoned ordinary input during the awaited native `agent/created` boundary, before initialization releases queued work. The caller supplies operation IDs backed by persisted ordinary-admission receipts. The companion removes only those proven unclaimed inputs through native inbox operations. Human inputs and explicitly accepted operator queues remain intact. Unrecognized managed pending input blocks activation before any removal. Claimed input remains native history; recovery never edits journal files to reconstruct or replay it.

Native restoration can close an interrupted turn before the new Agent emits lifecycle events. During creation, the companion therefore reconciles claimed receipts against the committed native inbox splices, exact input ID and operation marker, recorded claim sequence, owning turn and terminal boundary. Proven receipts retain their original execution identity and acquire the native terminal outcome. Incomplete or mismatched proof leaves the receipt unresolved. This read-only reconciliation neither inserts input nor changes the journal.

The native tests in `tests/integration/agents/dsh/web/test_native_control.py` exercise authentication, true-idle maintenance, both admission orders, post-preparation lifetime loss, exact receipts, guarded reset, scoped interruption, and crash-before-claim recovery with a controlled local model. These tests use synthetic credentials and do not constitute live-provider qualification.

## Accounting Scope and Recovery

The runtime persists its native journal attachment boundary before publishing browser authority. The verified native identity establishes the logical agent, runtime session and generation even before the first public manifest exists. Restoring the same conversation reuses the original binding, offsets and finalized rows. A new host's metadata channel includes preactivation abandonment proof, while its creation does not move the native historical boundary.

Native request attempts supply usage, terminal outcomes and actual model/provider routes. Browser changes therefore affect later requests without relabeling earlier records. Companion input IDs and native claim sequences associate managed operations before immutable finalization. Ordinary browser turns require no Houmao submission and appear as native-observed records. Runtime context, skill catalog and time messages do not count as human input.

Human steering within a managed native turn produces one charged record with the `dsh_web_mixed_input` diagnostic. Terminal receipts expose `mixed_input` and metadata-only `input_claims`; incomplete claim history reports `unknown`. A distinct human follow-up keeps its own native turn and usage even if it finishes before the earlier managed caller returns. Sender-specific token shares are unavailable. The qualified native build consumes explicit next-turn operator inputs separately. If verified claims ever establish several managed operations in one turn, the earliest claim retains the charge; other operation records identify shared accounting and leave their sender allocation unavailable.

Journal and metadata checkpoints commit observations transactionally. Repeated collection and API reconnection do not create another charge. Concurrent collectors preserve the original generation and immutable evidence cutoff. Missing, replaced, incomplete or discontinuous claim evidence produces an explicit collection limitation; recovery never submits input to reconstruct accounting. A definitive refused operation and a proven abandoned unclaimed operation have no reported provider measurement. An uncertain transport failure remains pending until native evidence resolves it.

The controlled native checks in `tests/integration/agents/dsh/web/test_usage.py` cover mixed input, separate human follow-up, actual changed model routes, pre-attachment history exclusion, operator queues, recorder reconstruction and exact host relaunch. The hermetic checks in `tests/unit/agents/realm_controller/test_dsh_web_usage.py` also cover concurrent first finalization, source gaps, journal replay and preactivation abandonment on a replacement metadata source. Neither suite loads provider credentials or makes paid requests.
