## Context

`houmao-server` currently exposes two public shapes:

- CAO-compatible `/sessions/*` and `/terminals/*` routes delegated through the child `cao-server`
- Houmao-owned terminal-tracking routes under `/houmao/terminals/{terminal_id}/*`

Both server-owned registration and live tracking are terminal-centric today. The current registration bridge is modeled as a delegated launch registration, it backfills `terminal_id` from child CAO when omitted, and the in-memory tracker registry is keyed around tracked TUI sessions plus terminal aliases.

That works for CAO/TUI sessions, but it does not fit headless Claude sessions well. The runtime already gives headless sessions a cleaner machine contract than the TUI path:

- a persisted runtime manifest and session root
- a stable tool-native resume identifier in `headless.session_id`
- per-turn artifact directories with `stdout.jsonl`, `stderr.log`, and exit status
- a tmux container for inspectability without requiring prompt delivery through `tmux send-keys`

The main constraints for this design are:

- existing CAO-compatible routes must remain intact
- current `/houmao/terminals/{terminal_id}/*` routes should remain available for TUI compatibility and richer TUI-only state
- headless agents should not be forced into fake `terminal_id` semantics
- headless launch and turn execution should stay Houmao-native instead of being funneled through child CAO
- `houmao-server` should keep explicit server-owned authority over admitted agents instead of introducing broad passive filesystem crawling
- the new shared state surface should stay small and transport-neutral, aligning with the direction of the ongoing server state-model simplification

The current server layout already provides the natural native-storage seam for that authority. `HoumaoServerConfig` separates `sessions_dir` for terminal-backed registration from `state_dir` for server-owned state, and the existing compatibility state already lives under `state/terminals/`. Native headless authority should follow that same server-owned state-tree pattern instead of extending the TUI registration bridge.

## Goals / Non-Goals

**Goals:**
- Add a first-class Houmao-owned HTTP API for managed agents that works across both TUI and headless transports.
- Keep read-side discovery and coarse state shared where the contract is honest for both transports.
- Make headless launch and stop server-native rather than CAO-delegated.
- Make headless prompt submission and inspection HTTP-native and turn-oriented instead of raw terminal-oriented.
- Preserve existing CAO-compatible and TUI compatibility routes without breaking current clients.
- Reuse runtime-owned manifest and turn-artifact evidence for headless tracking instead of inventing a second incompatible headless state source.

**Non-Goals:**
- Replacing CAO-compatible `/sessions/*` and `/terminals/*` routes with the new API.
- Requiring TUI agents to use the new headless turn-control routes in v1.
- Adding SSE, WebSocket, or other streaming push contracts in this change.
- Making `houmao-server` discover arbitrary local headless runtime manifests without explicit server-owned launch or authority.
- Redesigning the full rich TUI tracking payload exposed on `/houmao/terminals/{terminal_id}/*`.

## Decisions

### Decision 1: Add a new shared `/houmao/agents/*` surface and keep terminal routes transport-specific

**Choice:** Introduce a transport-neutral managed-agent API under `/houmao/agents/*` for shared discovery, identity lookup, coarse state, and bounded history:

- `GET /houmao/agents`
- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/state`
- `GET /houmao/agents/{agent_ref}/history`

Existing CAO-compatible `/sessions/*` and `/terminals/*` routes remain unchanged. Existing `/houmao/terminals/{terminal_id}/*` routes remain TUI-focused compatibility routes and continue to expose richer TUI-only tracking details.

**Rationale:**
- Shared discovery and coarse state are useful across both transports.
- Raw terminal output and terminal input are not honest abstractions for headless sessions.
- Preserving `/houmao/terminals/*` avoids forcing current TUI consumers onto a smaller cross-transport contract.

**Alternatives considered:**
- Put headless agents under `/terminals/{terminal_id}`: rejected because headless agents do not naturally have `terminal_id` semantics.
- Make `/sessions/*` a mixed TUI plus headless discovery surface: rejected because those routes are part of CAO compatibility.
- Expose only headless-specific routes with no shared agent API: rejected because discovery and coarse state are naturally cross-transport.

### Decision 2: Use native Houmao launch for headless agents and keep registration only for TUI compatibility

**Choice:** Split authority by transport:

For TUI registrations:
- `terminal_id` remains the compatibility alias
- current tmux window enrichment behavior remains unchanged

For headless agents:
- `houmao-server` owns launch directly through a Houmao-native headless launch endpoint
- the server itself materializes the runtime manifest, session root, and tracked-agent identity
- the server persists a dedicated authority record under `<server_root>/state/managed_agents/<tracked_agent_id>/authority.json`
- the server does not rely on delegated CAO launch registration to admit headless agents

The server does not admit arbitrary local headless manifests into public API authority without explicit server-owned launch or another future explicit Houmao-owned admission path.

The headless authority record is intentionally small and server-owned. At minimum it should carry:

- `tracked_agent_id`
- `tool`
- `manifest_path`
- `session_root`
- `tmux_session_name`
- optional `agent_name`
- optional `agent_id`
- server-owned lifecycle timestamps or equivalent bookkeeping

**Rationale:**
- Headless sessions are already Houmao-native in the runtime architecture and do not need CAO to create or resume them.
- This keeps CAO contained to the TUI compatibility slice instead of leaking CAO assumptions into the headless transport.
- It avoids a misleading design where `houmao-srv-ctrl launch --headless` still depends on CAO sessions and terminal ids after claiming to be headless.

**Alternatives considered:**
- Reuse the existing registration bridge for headless too: rejected because it keeps headless attached to CAO-shaped lifecycle even though headless is Houmao-native.
- Scan runtime roots for manifests on every startup: rejected because it broadens authority in an uncontrolled way and weakens the server-owned registration model.
- Use the shared registry as the primary admission source: rejected because the existing server design intentionally treats it as compatibility evidence rather than the main authority.

### Decision 2A: Persist active headless turn authority separately from the runtime manifest

**Choice:** Persist the currently active server-managed headless turn under the same managed-agent authority subtree at `<server_root>/state/managed_agents/<tracked_agent_id>/active_turn.json`.

That active-turn record is server authority for:

- single-active-turn admission gating
- post-restart interrupt targeting
- restart-time turn reconciliation

At minimum it should carry:

- `tracked_agent_id`
- `turn_id`
- `turn_index`
- `turn_artifact_dir`
- `started_at_utc`
- live targeting metadata such as tmux session and window identity when available

On startup, `houmao-server` reconciles `active_turn.json` against live tmux evidence and durable turn artifacts before it admits another turn for that agent or treats the agent as idle. If the earlier turn is still live, the server restores active-turn authority. If the earlier turn has already reached a terminal state, the server clears the active-turn record and reopens admission for the next turn.

**Rationale:**
- The runtime manifest persists resumable session identity, not server-owned turn admission authority.
- Current interrupt and terminate behavior depends on in-memory runner fields, which is not enough for restart-safe server semantics.
- A small dedicated active-turn record is clearer than trying to overload the runtime manifest with server-local control-plane concerns.

**Alternatives considered:**
- Keep active-turn authority in memory only: rejected because single-active-turn gating and `/interrupt` become undefined after restart.
- Store active-turn authority only inside runtime manifests: rejected because manifests are runtime-owned reconnect state, while this turn lock is server-owned API authority.

### Decision 3: Introduce one server-owned managed-agent identity with alias resolution

**Choice:** Add a server-owned stable tracked agent identity for `/houmao/agents/{agent_ref}` lookups. `agent_ref` resolves through a small alias layer:

- server-owned tracked agent id
- `terminal_id` and `session_name` for TUI-backed agents
- runtime session identity, `agent_id`, and `agent_name` when available

Alias resolution remains explicit and reject-on-ambiguity rather than silently choosing one match.

**Rationale:**
- TUI and headless agents need one shared lookup surface without pretending they share the same native identifier.
- Existing TUI terminal aliases still matter for compatibility, but they should be aliases, not the primary cross-transport key.
- Headless agents already have several meaningful identities; the API needs one server-owned stable key plus explicit alias rules.

**Alternatives considered:**
- Keep `terminal_id` as the only public key: rejected because it cannot represent headless sessions honestly.
- Use runtime `session_id` as the universal public id: rejected because TUI and headless backends do not share one universal runtime identifier shape.

### Decision 4: Back the shared state API with transport-specific trackers projected into a small common model

**Choice:** Keep transport-specific tracking internally, but project both into a small shared state contract for `/houmao/agents/*`:

- `identity`
- `transport`
- `availability`
- `turn`
- `last_turn`
- optional `diagnostics`

TUI agents derive this shared model by projecting the richer existing tracked-state data. Headless agents derive it from manifest state, active turn bookkeeping, tmux liveness, and per-turn artifact evidence.

The richer TUI payload on `/houmao/terminals/{terminal_id}/state` remains available and is not replaced by the shared model.

Shared `/houmao/agents/{agent_ref}/history` remains bounded coarse recent managed-agent history across both transports. For headless agents, durable detail stays on `/turns/{turn_id}` instead of being duplicated into `/history`.

**Rationale:**
- The shared API only needs the fields that are stable across both transports.
- TUI already has deeper parser- and lifecycle-oriented state that would be dishonest or meaningless for headless agents.
- Headless state is simpler and more deterministic; the shared projection should not inherit TUI-only baggage.

**Alternatives considered:**
- Reuse the existing TUI state model verbatim for headless agents: rejected because fields such as `parsed_surface` and lifecycle authority do not fit.
- Create totally unrelated TUI and headless read APIs: rejected because discovery and coarse posture are shared concerns.

### Decision 5: Headless lifecycle is modeled as native launch plus turn resources

**Choice:** Headless-only write routes are modeled as one native launch entrypoint plus turn resources:

- `POST /houmao/agents/headless/launches`
- `POST /houmao/agents/{agent_ref}/stop`
- `POST /houmao/agents/{agent_ref}/turns`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/events`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stdout`
- `GET /houmao/agents/{agent_ref}/turns/{turn_id}/artifacts/stderr`
- `POST /houmao/agents/{agent_ref}/interrupt`

`POST /houmao/agents/headless/launches` creates one server-managed headless agent from resolved runtime launch inputs. In v1, the request should be explicit and narrow:

- `tool`
- `working_directory`
- `agent_def_dir`
- `brain_manifest_path`
- `role_name`
- optional `agent_name`
- optional `agent_id`

The raw HTTP contract does not treat `provider`, `agent_source`, or installed profile names as the normative launch inputs. Those are pair convenience concepts for higher-level tools.

Validation failures such as missing resolved launch inputs, inconsistent tool-versus-manifest data, or convenience-only request shapes should fail explicitly with validation semantics rather than being interpreted heuristically.

The launch result returns the tracked-agent identity plus server-owned manifest/session-root pointers and any tmux identity needed for later inspection.

`POST /turns` accepts one prompt turn for a launched headless agent and returns an accepted turn record. A headless agent may have at most one active server-managed turn at a time in v1; additional prompt submissions fail explicitly while a turn is active.

These routes reject TUI-backed agents explicitly. TUI prompt delivery remains on existing terminal input surfaces for now.

**Rationale:**
- Headless launch is a different lifecycle operation from turn execution and should not be smuggled through registration.
- Headless CLI sessions already operate as discrete resumed turns after launch.
- A resolved runtime request model is easier to validate consistently and fits the current runtime seams better than pair-style convenience inputs.
- This matches the underlying Claude/Gemini/Codex headless contract much better than raw input injection.
- Polling turn resources is simpler and less risky for v1 than introducing streaming protocols immediately.

**Alternatives considered:**
- Keep launch out of the API and require another local tool to pre-create headless manifests: rejected because `houmao-srv-ctrl launch --headless` needs a first-class server target.
- Accept pair convenience inputs such as `provider` and `agent_source` as the raw HTTP contract: rejected because that blurs the existing install-versus-launch split and couples the native route back to CAO/profile-era concepts.
- Reuse `POST /terminals/{terminal_id}/input` for headless: rejected because headless sessions do not accept prompt delivery through raw terminal input.
- Force both TUI and headless into one shared write route in v1: rejected because the execution models are not equivalent yet.
- Add SSE/WebSocket streaming in the first cut: rejected to keep the surface smaller and easier to verify.

### Decision 6: `houmao-srv-ctrl launch --headless` targets the native server launch path instead of delegating to `cao`

**Choice:** Keep `houmao-srv-ctrl launch` split by mode:

- default or TUI-shaped launch continues through delegated `cao launch`
- additive `--headless` launch targets `houmao-server` directly through the native headless launch route

For the headless case, `houmao-srv-ctrl` owns translation from pair convenience inputs such as `--agents` and `--provider` into the resolved native request expected by `houmao-server`. That translation may reuse existing pair install and runtime-builder flows, but the raw server launch route stays native and explicit.

This is intentionally asymmetric. CAO compatibility remains the TUI path. Headless is a Houmao-owned extension path.

**Rationale:**
- It keeps the public operator entrypoint stable while avoiding a fake CAO dependency for headless work.
- It matches the product boundary: CAO compatibility is preserved where needed, but Houmao-native features do not need to route through CAO just because they share a CLI verb.
- It avoids synthesizing CAO `session_name` and `terminal_id` for work that never needed them.

**Alternatives considered:**
- Delegate all launch forms to `cao`: rejected because it blocks Houmao-native headless ownership.
- Forward `--agents` and `--provider` directly as the raw server launch contract: rejected because the accepted boundary is that convenience translation belongs in the CLI, not the HTTP route.
- Introduce a separate `houmao-srv-ctrl launch-headless` command immediately: rejected because additive `--headless` is enough for this change and keeps the operator surface smaller.

### Decision 7: Reuse runtime headless execution and parsing helpers through a shared library seam

**Choice:** `houmao-server` should not reimplement the headless CLI contract independently. Instead, machine-readable turn execution and artifact/event interpretation should be factored into reusable runtime-owned helpers that both the existing runtime and the new server routes can call.

The shared seam should cover:

- constructing a manifest-bound headless session handle
- creating and stopping one native headless session from resolved runtime launch inputs
- starting one resumed headless turn
- reading turn lifecycle status from durable artifacts
- parsing structured `stdout.jsonl` events into server-facing event models

**Rationale:**
- The runtime already knows how to execute and interpret headless turns.
- Duplicating that logic in `houmao-server` would create drift in event parsing and resume handling.
- Reusing runtime launch helpers does not make runtime manifests the server authority; `authority.json` and `active_turn.json` remain the server-owned control-plane truth.
- A shared library seam keeps the server API aligned with the actual headless runtime contract.

**Alternatives considered:**
- Make `houmao-server` shell out to runtime CLI commands: workable for debugging, but too indirect and brittle for the primary API path.
- Reimplement headless turn parsing inside `houmao-server`: rejected because it duplicates semantics that already exist in runtime code.

## Risks / Trade-offs

- [Shared state becomes too coarse for existing TUI consumers] → Keep `/houmao/terminals/{terminal_id}/*` intact for rich TUI-specific inspection while `/houmao/agents/*` stays intentionally smaller.
- [Server-owned headless authority adds a second persisted store beside runtime manifests] → Keep the server store small and pointer-oriented: `authority.json` and `active_turn.json` define admission and reconciliation, while runtime manifests remain runtime-owned backend state.
- [Two launch paths make the pair architecture less uniform] → Keep the split explicit: CAO-backed TUI compatibility on one side, Houmao-native headless lifecycle on the other, with the shared `/houmao/agents/*` surface unifying read-side inspection.
- [Concurrent headless turn submission causes conflicting CLI resumes] → Gate v1 to one active server-managed headless turn per agent and reject overlapping submissions explicitly.
- [Runtime and server drift on headless event interpretation] → Factor shared headless helpers instead of keeping two parsers.
- [Native headless launch needs more launch-input modeling than TUI registration] → Keep the headless launch request explicit and narrow in v1 around already-supported runtime inputs such as `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and `role_name`, and let `houmao-srv-ctrl` absorb convenience translation.

## Migration Plan

1. Add the new `/houmao/agents/*` routes plus native headless launch and stop routes as additive Houmao-owned extensions, backed by a dedicated `state/managed_agents/<tracked_agent_id>/` authority subtree.
2. Keep all existing CAO-compatible and `/houmao/terminals/{terminal_id}/*` routes unchanged so current callers do not need to migrate immediately.
3. Update `houmao-srv-ctrl launch --headless` to translate pair convenience inputs into the resolved native launch request while keeping delegated `cao launch` for TUI-shaped sessions.
4. Migrate new headless-aware clients to `/houmao/agents/*`, `/turns/{turn_id}`, and the bounded coarse `/history` surface while keeping old TUI-only consumers on terminal routes until they choose to adopt the shared surface.

Rollback is straightforward because the change is additive: disable or remove the new managed-agent routes and native headless path while leaving existing compatibility and terminal routes untouched.

## Open Questions

- Whether a later change should let TUI-backed prompt submission converge on a turn resource model similar to headless. This design intentionally leaves that for later.
- Whether `/events` should gain cursor-based incremental polling in a follow-up once the basic headless API is in place.
