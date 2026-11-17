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
| `observe_common_plugins(identity)` | `common_state` | Compare current effective skill/MCP inputs with native resource evidence without applying configuration |
| `refresh_common_plugins(identity, timeout_seconds=...)` | `refresh` | Observe first, then return a verified no-op or claim native maintenance for non-restarting resource refresh |
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

## Common Plugin Observation and Refresh

The qualified `0.2.2-rc.3` Web profile supports common observation and configuration/resource refresh through its launch-time companion. These operations consume current native home material and retain launch-overlay precedence. They do not rebuild the home from Houmao launch manifests or read edited launch profiles. A home patch masked by a retained command-line overlay remains masked.

`common_state` compares visible filesystem skill providers against a separate native filesystem-provider read. Public native runtime-fiber records include directly mounted preset providers as well as Loader entries. The qualified bundled Office provider also gets an independent native asset read. These reads leave the running registry's cache and watchers untouched. Scope precedence includes the bound agent's mounted preset, global providers, and inherited scopes. Opaque includes, unqualified expressions, unverified provider conflicts, or changes during the comparison retain incomplete or unknown evidence.

An unqualified native skill dependency or provider contribution prevents complete coverage, including a cached empty provider. Its visible common inventory remains available without inferring source freshness from the cache. This is common-resource coverage, not a native-special-plugin inventory. Native extension package versions remain outside the common inventory.

Skill catalog freshness concerns discovery metadata. Skill bodies have a `next_load` boundary because the filesystem provider reads them when requested. Earlier loaded instructions remain in conversation history. Autonomous watchers may update discovery without a Houmao receipt; a complete matching observation permits `already_current` with `method=noop`.

MCP declarations are compared privately with the effective native manager configuration. Tool freshness additionally requires a captured connection-generation event for that manager, the matching declaration and native connection state, and matching scoped tool registration. A connection that predates available evidence remains unknown. Server implementation freshness is a separate optional component and remains unknown for an enabled subprocess: declaration/tool freshness does not establish the latest externally edited package revision. Credentials, raw declarations and skill bodies are excluded from observations.

Mutating refresh claims `runMaintenance` immediately and rechecks owner authority, the exact identity, pending input/interactions, and other native agents sharing host resources. Busy or uncertain admission refuses immediately. Configuration is reconciled using native APIs; visible filesystem providers are restarted as resources, and configured MCP instances reconnect. When present, a native HMR service supplies serialization around configuration reconciliation. A busy serializer refuses without leaving a deferred mutation. Refresh does not invoke its hot-code replacement planner or source-watch reload/exit path, which can affect lifecycle providers. Agent/control lifecycle configuration edits require separate explicit relaunch. Observation evidence explicitly identifies the configuration/resource scope and unsupported hot-code HMR.

While refresh owns shared resources, a serial native `agent/created` hook also refuses competing Agent activation before initialization releases queued work. Native creation rolls back that attempted activation. This closes the race in which browser or child activation starts after the initial live-agent check. Autonomous resource watchers remain enabled.

Native reconciliation can apply broader configuration and extensions and can fail after applying some changes. Common freshness, native diagnostics, effects and readiness therefore remain separate. An unrelated host module pending until restart does not invalidate confirmed common resources. A failed extension can coexist with confirmed current common state and retains its failure diagnostic. Houmao makes no common inventory or version guarantee for native-special-plugin packages.

The runtime uses a separate authenticated API connection for the long refresh request. State reads and interruption retain their own connection. One absolute monotonic deadline covers gateway reads, authentication, client serialization, native observation and final admission. The owned local Linux host retains that deadline across the wire; native code checks it before configuration handoff and every independent provider/MCP restart. Authentication and observation cannot reset the budget. Already-admitted native calls may settle after the deadline, but no later managed resource step starts.

The backend also receives the service's captured native identity. It checks that identity before authentication, snapshots it for the request, and refuses a replacement published during authentication. The native companion rechecks the same identity at admission. A later reset or relaunch therefore cannot receive the earlier refresh request.

A timeout does not retry, roll back, restart, or release native maintenance early. Passive common observation reports unsettled state until the original native maintenance promise finishes. Invalid readiness keeps maintenance held to prevent its native `finally` block from waking queued input; explicit lifecycle recovery remains separate.

The controlled suite `tests/integration/agents/dsh/web/test_refresh.py` executed 26 cases against the selected rc.3 executable, with synthetic credentials, a loopback model endpoint, and zero model requests caused by refresh. It covers skill/MCP add/update/remove, independent Office asset comparison, opaque and empty provider coverage, watcher updates before and during managed refresh, loaded skill history and later body loads, unreachable MCP health versus applied declarations, no-op, distinct homes, existing shared children and activation races, browser-turn admission races, busy maintenance/serialization, malformed input, failed replacement, lifecycle refusal, absolute deadline expiry during preflight and before later resource steps, native timeout, actual HTTP response loss, and invalid-readiness containment through explicit native disposal. Ordinary browser/skill history cases explicitly create their own controlled model turns; refresh creates none.

`test_refresh_gateway.py` separately qualifies the actual managed runtime and public gateway routes, including native-home resolution and stopped-Agent refusal, pending/current mapping, no-op and actual MCP tool evidence. Its second test serves two actual gateways and the passive server, then exercises scoped CLI, direct gateway and passive-client requests against both agents. Those tmux fixtures clear inherited selectors and use an explicit unique socket. Native-home resolution validates the live captured primary pane plus session manifest/agent bindings. It accepts a headless envelope between workers and refuses a thin joined fallback directory without a matching native selector.

`native-refresh-probe.mjs` injects controlled pending/failure results and a reload barrier around actual native configuration application. Those protocol checks do not qualify arbitrary extension lifecycle behavior. The installed configuration-only profile is directly tested. HMR locking uses the inspected public API; hot-code replacement remains outside this refresh path.

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
