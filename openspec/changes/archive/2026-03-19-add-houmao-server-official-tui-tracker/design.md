## Context

`houmao-server` already owns the public server boundary, but its current watch implementation is still a thin CAO-backed poller in [src/houmao/server/service.py](/data1/huangzhe/code/houmao/src/houmao/server/service.py). It asks the child `cao-server` for terminal status and output, reduces only a small amount of state, and writes file-backed watch mirrors. The richer TUI parser and tracker logic lives elsewhere: demo-only monitor code in [src/houmao/demo/cao_dual_shadow_watch/monitor.py](/data1/huangzhe/code/houmao/src/houmao/demo/cao_dual_shadow_watch/monitor.py) and runtime-local turn monitoring in [src/houmao/agents/realm_controller/backends/cao_rest.py](/data1/huangzhe/code/houmao/src/houmao/agents/realm_controller/backends/cao_rest.py).

That split no longer matches the intended architecture. We want `houmao-server` to replace more CAO-owned behavior, and the first replacement step is TUI parsing and continuous live state tracking. The server should actively watch all known Houmao tmux-backed sessions whether or not a client is querying state, determine TUI up/down from actual processes instead of scrollback guesses, parse supported TUI surfaces directly from tmux capture, and keep the authoritative live state in memory.

This change is intentionally narrower than a full runtime or demo rewrite:

- CAO-compatible session-control routes may still use the child CAO adapter for now.
- Demo consumption is out of scope.
- File-backed watch artifacts are out of scope for the new live tracking design.
- The parser core already defined by the repo remains useful, but within `houmao-server` it becomes the official parser boundary rather than a "shadow" helper.
- The existing `houmao-server` session registration bridge remains in scope and becomes the primary discovery seed for the sessions this server manages.
- The external route migration stays narrow in v1: the existing terminal-keyed extension routes remain the public lookup surface while the internal tracker moves to Houmao-owned identity.

CAO is still useful as an architectural hint. Its `tmux client -> provider -> service` separation is a good layering pattern, but its coarse provider `get_status()` contract is too lossy for Houmao's needs. Houmao needs a richer pipeline: probe tmux and processes, parse the visible surface, and then track live state over time.

## Goals / Non-Goals

**Goals:**
- Make `houmao-server` the authoritative owner of continuous TUI parsing and live state tracking for known tmux-backed Houmao sessions.
- Remove `cao-server` from the parsing and state-tracking path.
- Use direct tmux and process inspection to distinguish tmux liveliness from TUI process liveliness.
- Keep the authoritative watch state fully in memory, with bounded recent transitions also retained in memory.
- Reuse the shared parser core through server-owned official parser naming and integration instead of inventing a second parser stack.
- Preserve a clean boundary between the watch plane and the separate CAO-compatible control plane.

**Non-Goals:**
- Not removing the child CAO adapter from every `houmao-server` route in the same change.
- Not designing or updating demo dashboards to consume the new state.
- Not persisting per-terminal watch snapshots or append-only watch logs to disk for this subsystem.
- Not changing unsupported-tool behavior; v1 remains focused on the currently supported parsed TUI tools.
- Not solving request-relative turn completion for every runtime path in the same change. Continuous live tracking is the first-class concern here.

## Decisions

### 1. Split the server watch path into probe, parse, and track stages

**Choice:** Use a three-stage pipeline inside `houmao-server`:

1. transport/process probing,
2. official TUI parsing,
3. continuous live state tracking.

The server worker loop should not collapse those concerns into one provider-like `get_status()` method.

**Rationale:** CAO's layering is good, but its provider status model loses too much information too early. Houmao needs to represent:

- tmux alive but tool process down,
- tool process alive but parser failed,
- parsed surface blocked or working,
- stability timing and recent transitions.

That is easier and cleaner when probing, parsing, and tracking are explicit stages.

**Alternatives considered:**
- Copy CAO's provider `get_status()` pattern directly: rejected because it compresses transport, parsing, and lifecycle into one coarse status call.
- Keep the existing server reducer and only improve the CAO payloads: rejected because the watch path would still depend on CAO output routing.

### 2. Use one background worker per known tmux session

**Choice:** The server should run one worker thread per known tmux-backed session, with a lightweight supervisor thread that reconciles the known-session registry against active workers.

Worker lifetime should follow tmux session lifetime:

- tmux exists: worker remains active
- tmux missing: worker finalizes state and exits

TUI process down does not end the worker.

**Rationale:** This matches the requested semantics directly and keeps the lifecycle model simple. The worker represents "the server is responsible for understanding this live tmux container," not "the tool is currently healthy."

**Alternatives considered:**
- One global polling loop over all sessions: rejected because per-session workers are easier to reason about, isolate, and test.
- Spawn workers only on state queries: rejected because the goal is continuous background tracking.

### 3. Define "known session" using Houmao-owned identity and server-owned registration seeding

**Choice:** The internal tracking target should be keyed by Houmao session identity, including at minimum:

- tool,
- agent/session identity,
- tmux session name,
- optional tmux window coordinates,
- optional compatibility `terminal_id`.

For this change, the known-session registry should be seeded from `houmao-server`'s own registration bridge (`sessions/<session_name>/registration.json`) for the sessions this server manages. That registration seed should be enriched with manifest-backed metadata and verified against live tmux liveness. Shared live-agent registry records and any child-CAO metadata may be consulted as compatibility evidence or alias-enrichment inputs, but they should not become the primary authority that admits a session into background tracking.

**Rationale:** The watch plane is moving away from CAO. `terminal_id` can remain useful for compatibility routes, but it should not be the primary identity of the tracking system.

**Alternatives considered:**
- Keep `terminal_id` as the watch authority: rejected because it keeps the model CAO-shaped even after the parser/state path becomes server-owned.
- Discover only from live tmux without Houmao metadata: rejected because it makes ownership ambiguous and risks watching unrelated sessions.
- Use runtime manifests plus shared-registry freshness as the primary discovery authority for this change: rejected because the current `houmao-server` direction keeps shared registry in a transitional compatibility role instead of promoting it to primary watch authority.

### 4. Keep the existing terminal-keyed extension routes as the v1 public lookup surface

**Choice:** The v1 public query surface should remain the existing terminal-keyed Houmao extension routes. `houmao-server` should maintain a compatibility alias map from `terminal_id` to its internal tracked-session identity and resolve public lookups through that map instead of keying the internal watch plane by `terminal_id`.

This change should not add a new session-keyed public route family. The route shape remains stable while the internal authority moves to Houmao-owned identity.

**Rationale:** This closes the identifier ambiguity without turning the same change into a route, client, and migration rewrite. The architectural win comes from moving the watch authority and state store away from CAO identity, not from forcing a second external route family immediately.

**Alternatives considered:**
- Add a new session-keyed route family as the primary v1 contract: rejected for this change because it would bundle public API churn into the same step as the watch-plane rewrite.
- Keep both the public contract and the internal store keyed primarily by `terminal_id`: rejected because it preserves CAO-shaped authority all the way through the new tracker.

### 5. Determine TUI up/down from process inspection, not scrollback heuristics

**Choice:** Each worker should inspect the tmux pane's live process tree to determine whether the supported tool TUI is up. Only when the tool process is present should the server capture pane text and run the parser.

When tmux exists but the tool process is absent, the tracked state becomes `tui_down` or equivalent and parsing is skipped for that cycle.

**Rationale:** This directly follows the requirement in the exploration. A dead or not-yet-started TUI should not be inferred from stale pane text. Process inspection is the right authority for TUI liveliness.

**Alternatives considered:**
- Infer TUI up/down from last parsed scrollback state: rejected because stale output can look healthy long after the process is gone.
- Ask CAO for terminal status: rejected because the new watch path must not depend on CAO.

### 6. Keep watch state authoritative in memory and stop writing watch files

**Choice:** The authoritative watch state store should live entirely in server memory. Per-session state and bounded recent transitions should be retained in memory only. The new design should not write `current.json`, `samples.ndjson`, or `transitions.ndjson` for live TUI tracking.

**Rationale:** The user explicitly asked for in-memory tracking with no file writes. This also removes ambiguity about where the live truth is.

**Operational consequence:** On server restart, watch state is rebuilt from rediscovered live sessions instead of loaded from prior watch artifacts.

**Alternatives considered:**
- Keep writing compatibility mirror files while treating memory as authoritative: rejected because it directly violates the simplification goal for this change.
- Move watch state to SQLite: rejected because it still creates a persistence contract we do not want yet.

### 7. Reuse shared parser and runtime primitives, but expose them under official server-owned naming

**Choice:** Reuse the existing shared parser stack and provider parsers, but wrap them in server-owned "official TUI parser" terminology inside `houmao-server`. Reuse or promote neutral tmux helpers from the shared runtime layer, keep manifest and compatibility-registry helpers in their existing modules, and let the new `src/houmao/server/tui/` subtree own only server-local orchestration, worker lifecycle, and in-memory state management.

A likely module shape is:

```text
src/houmao/server/tui/
  transport.py
  process.py
  registry.py
  tracking.py
  supervisor.py
```

with thin adapters into the shared parser and shared runtime helpers instead of duplicating parser selection or tmux utilities.

**Rationale:** The repo already has reusable parser, tmux, manifest, and registry primitives with tests and existing call sites. What needs to change is the server boundary and naming, not the underlying parsing science or every shared helper location.

**Alternatives considered:**
- Rename the entire shared parser capability immediately and move all modules at once: rejected because it creates larger churn than this change needs.
- Leave server-facing names as "shadow parser": rejected because inside `houmao-server` this parser is now the authoritative one.
- Copy tmux or manifest helpers into a new server-only utility stack: rejected because it would create parallel helper layers for the same runtime facts.

### 8. Make continuous live state primary, and request-relative completion secondary

**Choice:** The primary tracked model should be continuous live state:

- tmux transport state,
- TUI process state,
- parsed surface state,
- derived operator state,
- stability timing,
- bounded recent transitions.

Request-relative completion and similar submit-aware semantics should be treated as a later optional layer on top of continuous live tracking rather than the core watch contract for this change.

**Rationale:** The server is now watching sessions continuously, not only around prompt submission. The old readiness/completion model from runtime-local turn monitoring is not the right top-level abstraction for this subsystem.

**Alternatives considered:**
- Make turn completion the primary tracked state: rejected because it is submit-relative and does not describe idle or TUI-down sessions well.

### 9. Expose an explicit tracked-state contract instead of a single summarized status

**Choice:** The live tracked-state contract should explicitly distinguish probe, process, and parse outcomes rather than collapsing them into one summarized operator status.

At minimum, the v1 state shape should include:

- Houmao-owned tracked-session identity,
- any `terminal_id` compatibility alias,
- `transport_state`,
- `process_state`,
- `parse_status`,
- optional `probe_error`,
- optional `parse_error`,
- nullable `parsed_surface`,
- derived `operator_state`,
- stability metadata, and
- bounded recent transitions.

The v1 public routes remain terminal-keyed, but they should return this richer state contract rather than only a coarse CAO-shaped status.

**Rationale:** The whole point of the probe/parse/track split is to preserve distinctions such as "tmux alive but TUI down" and "TUI up but parser failed." If the public state collapses back to one top-level status, the new architecture loses most of its value.

**Alternatives considered:**
- Keep only one summarized operator-facing state on the wire: rejected because it hides the distinctions the new tracker is designed to surface.
- Expose parser internals only through logs or diagnostics instead of the main state route: rejected because it would make automation and failure diagnosis harder.

## Risks / Trade-offs

**[In-memory state disappears on restart]** → Rebuild watch state by rediscovering active known sessions at startup. Accept that recent transition history is ephemeral in this version.

**[Process detection may be tool-version-sensitive]** → Keep per-tool process matchers narrow and explicit, and back them with unit tests plus live smoke coverage for supported tools only.

**[One worker per tmux session may add thread overhead]** → Accept the simpler correctness model for v1. The expected live session count is modest, and optimization can come later if needed.

**[Terminology migration is awkward while the shared capability still says "shadow"]** → Keep server-facing naming official and explicit now, and limit low-level naming churn to the minimum needed for this change.

**[The active demo-focused stability-window change overlaps conceptually]** → This change defines the primary live-tracking and stability contract. The overlapping change should be narrowed to demo-only visualization or other consumption of server-owned state rather than a competing tracker contract.

## Migration Plan

1. Add server-owned tmux transport and process probing primitives.
2. Add the in-memory watch-target registry, supervisor, worker loop, and live state store.
3. Reuse the shared parser core through a server-owned official parser adapter.
4. Move the continuous reduction logic into the new server-owned tracker model.
5. Update `houmao-server` extension routes to read from in-memory state and bounded recent transitions.
6. Remove file-backed watch artifact writes from the live tracking path.
7. Add verification for direct tmux/process probing, official parser selection, worker lifecycle, and in-memory state exposure.

**Rollback:** Disable the new server-owned tracking path and restore the existing CAO-backed watch reducer. This change does not require a persisted data migration because the new authoritative state is in-memory only.

## Open Questions

- Should the bounded recent transition buffer be exposed inline on the state route, only through the history route, or both?
- Which supported tools are in scope for v1 official parser tracking beyond the currently tested Claude and Codex lanes?
