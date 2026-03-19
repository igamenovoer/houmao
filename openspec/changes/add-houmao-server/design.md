## Context

Today, Houmao reaches interactive HTTP-backed sessions primarily through `cao-server` and the repo-owned `CaoRestClient`, and CAO-native operator workflows still depend on the `cao` CLI. That gives Houmao working server and CLI boundaries, but both are owned by CAO. Persistent state watching is either request-scoped inside `cao_rest` waits or implemented in demo-only monitor code. Features such as continuous watch workers, server-owned state history, and Houmao-specific terminal status still sit outside the main server boundary.

The new target is not a per-session sidecar. It is a first-party server process named `houmao-server`, conceptually parallel to `cao-server`, plus a CAO-compatible command surface on `houmao-cli`. In the shallow first cut, `houmao-server` can start and supervise a child `cao-server` subprocess and dispatch most HTTP-compatible work to it, while `houmao-cli` can shell out to `cao` for most CAO-compatible CLI verbs. But callers should treat the Houmao surfaces as the authority, so the architecture can later replace CAO completely without another public-protocol reset.

Constraints:
- v1 must not require modifying CAO source code
- v1 should stay shallow and delegate most server and CLI work to CAO where that reduces implementation cost
- the public API should stay close enough to CAO routes and payloads that current Houmao-side REST patterns can migrate with minimal churn
- the new CAO-compatible CLI plan must account for the repository already reserving `houmao-cli` as the primary operator binary
- the shallow-cut child `cao-server` port must not become a user-facing configuration contract
- direct human interaction with the live TUI remains supported
- the resulting design must create a clean seam for replacing CAO later instead of baking CAO deeper into Houmao

## Goals / Non-Goals

**Goals:**
- Add a first-party `houmao-server` HTTP service that Houmao clients can target directly
- Preserve the targeted CAO HTTP endpoint surface so `houmao-server` can act as a drop-in replacement of `cao-server`
- Add a CAO-compatible command surface to `houmao-cli` so it can act as a drop-in replacement of `cao`
- Move persistent TUI watching and terminal-state publication into `houmao-server`
- Keep Houmao-specific status and watch features as explicit server extensions rather than demo-only logic
- Start with CAO-backed subprocess delegation while preserving a clean migration path to native Houmao-owned backend implementations

**Non-Goals:**
- Re-implementing most CAO behavior natively in the first implementation
- Supporting the child `cao-server` port as a public interface or documented operator surface in the shallow cut
- Allowing a user-facing option to set the child `cao-server` port independently from `houmao-server`
- Unifying `houmao-server` with the gateway into one service in this change
- Perfectly reconstructing human intent from direct manual TUI interaction
- Removing existing direct CAO flows in the same change

## Decisions

### Decision 1: Build one central `houmao-server` process with per-terminal workers, not per-session sidecars

**Choice:** Introduce one `houmao-server` process that exposes an HTTP API similar to `cao-server` and internally owns multiple live sessions and terminals. Persistent watch behavior runs in per-terminal workers managed by the server process, not as standalone sidecars spawned per session.

**Rationale:**
- Matches the product goal: replace `cao-server`, not add another companion around it
- Preserves the familiar CAO session/terminal mental model for callers
- Keeps watch services under one Houmao-owned server boundary rather than scattering them across sidecars
- Makes future native backend replacement a server-internal concern rather than another client-visible architecture change

**Alternatives considered:**
- Per-session supervisor sidecars: useful for monitoring, but the wrong public shape for a `cao-server` replacement
- Keep ephemeral in-process watchers only: does not solve the server-ownership problem

### Decision 2: Map the targeted CAO HTTP endpoint surface and add Houmao features on extension routes

**Choice:** `houmao-server` maps the targeted CAO HTTP endpoint surface, preserving route paths, methods, parameter names, and response shapes closely enough for drop-in CAO server replacement in the supported version. Houmao-specific watch and state features live on separate extension routes rather than overloading CAO-compatible payloads immediately.

**Rationale:**
- Minimizes migration cost for existing Houmao REST usage patterns
- Lets the new server replace CAO incrementally without forcing every caller to change at once
- Keeps Houmao-only behavior explicit and easier to evolve

**Alternatives considered:**
- Invent a completely different API immediately: increases migration cost and delays adoption
- Hide Houmao features inside CAO-compatible payloads from day one: makes compatibility and evolution harder to reason about

### Decision 3: In v1, `houmao-server` starts and supervises a child `cao-server` subprocess

**Choice:** `houmao-server` manages one child `cao-server` subprocess in the shallow cut. Most CAO-compatible HTTP routes dispatch inward to that child server rather than re-implementing CAO logic immediately. The child CAO port is derived mechanically as `houmao-server` port `+1`, and no user-facing interface may override it independently.

Direct traffic to the child CAO endpoint is treated as an unsupported user or debug hack rather than as a supported public surface, even though a caller who already knows the internal port can technically still reach it.

**Rationale:**
- Keeps v1 shallow and practical
- Preserves a simple drop-in story for callers while Houmao grows server-owned features around the child
- Avoids forcing Houmao to hide or rewrite every existing CAO integration point in one change
- Prevents the internal child-port choice from hardening into another long-lived public contract

**Alternatives considered:**
- Embed CAO as a library: tighter coupling and a less realistic migration seam
- Proxy to an externally managed CAO only: weaker lifecycle ownership for the Houmao server
- Let operators choose an arbitrary child CAO port: rejected because it turns an internal shallow-cut detail into a public configuration surface
- Re-implement CAO server behavior immediately: too much scope for the first cut

### Decision 4: Treat CAO as a replaceable upstream engine behind `houmao-server`

**Choice:** `houmao-server` owns the public HTTP API, persistent state, and watch-worker lifecycle. A CAO-backed adapter is responsible only for v1 upstream actions such as:

- creating and deleting upstream sessions or terminals
- reading terminal metadata and output
- sending prompt or control input
- interrupting or stopping upstream terminals

The server API and persisted state are Houmao-owned, and the upstream adapter kind is internal server metadata rather than the public identity of the service.

**Rationale:**
- Satisfies the "do not modify CAO" constraint
- Creates the replacement seam where CAO can later be swapped for native tmux or provider adapters
- Keeps CAO details out of Houmao-owned watch and status contracts

**Alternatives considered:**
- Extend CAO directly: faster initially, but it preserves the wrong ownership boundary
- Proxy CAO transparently with no Houmao-owned state model: does not buy the additional features this change needs

### Decision 5: Extend `houmao-cli` with a CAO-compatible command family instead of inventing a second wrapper binary

**Choice:** Because the repository already reserves `houmao-cli` as the primary operator binary, this change extends `houmao-cli` with a CAO-compatible command family rather than introducing a second wrapper name. For most CAO-compatible commands, `houmao-cli` shells out to the installed `cao` executable and preserves CAO-facing behavior as closely as practical.

**Rationale:**
- Avoids another user-facing binary rename while the repo already centers `houmao-cli`
- Keeps the shallow cut pragmatic by delegating most CLI behavior to the already-installed `cao`
- Creates a place to add Houmao-owned CLI-side behavior without waiting for full native replacement

**Alternatives considered:**
- Add a separate `houmao-cao` wrapper: duplicates the user-facing command story
- Re-implement the whole `cao` CLI immediately inside Houmao: too much scope for v1

### Decision 6: Register CAO-compatible launch results into `houmao-server`

**Choice:** For CAO-compatible CLI flows that create or launch a live agent session, `houmao-cli` performs the delegated CAO operation first and then registers the resulting live agent or session with `houmao-server`.

For v1, `launch` is the minimum required registration hook.

**Rationale:**
- Lets operators keep CAO-native launch habits while Houmao-server gains awareness of the resulting live sessions
- Avoids requiring every live agent to be created only through the server HTTP path on day one
- Keeps the registration seam explicit for eventual native replacement

**Alternatives considered:**
- Register nothing on CLI launch: leaves server-owned watch/state blind to CLI-created sessions
- Force all launches through `houmao-server` only: not a drop-in CAO CLI story

### Decision 7: Publish three distinct terminal state layers

**Choice:** `houmao-server` publishes three related but distinct views per live terminal:
- `raw_observation`: the latest parsed full-snapshot surface and supporting metadata
- `owned_work`: server-known queued or active requests, including which work item currently owns lifecycle tracking
- `operator_state`: a separately published operator-facing view derived from the observation stream and allowed to apply stability policy later without changing the core transport contract

When the raw surface changes materially without an active server-owned request, `houmao-server` records that change as external activity instead of inferring server-owned completion.

**Rationale:**
- Snapshot-derived state is inherently noisy and incomplete
- Owned request lifecycle must not be conflated with arbitrary operator typing in the live TUI
- A separate operator-facing layer gives the system room to apply stability windows without rewriting client contracts later

**Alternatives considered:**
- One flattened status blob: easier initially, but mixes evidence, ownership, and presentation concerns
- Treat all observed activity as if it came from server requests: incorrect when operators type directly in the TUI

### Decision 8: Reuse gateway-style storage and process patterns where useful, but keep `houmao-server` protocols distinct

**Choice:** `houmao-server` should reuse operational patterns that are already working elsewhere in the repo:
- atomic JSON state artifacts
- append-only NDJSON event and history logs
- explicit current-instance state
- small FastAPI/uvicorn server runtime
- adapter-based upstream boundaries

The server root and HTTP protocols remain `houmao-server`-specific because the API surface, multi-terminal lifecycle, and compatibility goals are different from the gateway's per-session control-plane focus.

**Rationale:**
- Reuses proven implementation techniques without forcing false protocol convergence
- Keeps implementation risk down while the new server boundary is still maturing
- Avoids another isolated subsystem with its own ad hoc persistence style

**Alternatives considered:**
- Files-only watch state with no server API: wrong fit for a `cao-server` replacement
- Immediate unification with gateway contracts: too much architectural scope for the first server cut

## Risks / Trade-offs

[A shallow CAO-backed first cut could become a permanent proxy layer] → Mitigation: keep the child-process and upstream-adapter boundaries explicit and keep CAO details out of public Houmao contracts.

[CAO-like compatibility may constrain API evolution] → Mitigation: keep the CAO-compatible routes stable and add Houmao-only behavior on explicit extension routes or compatibility-aware CLI hooks.

[Continuous watch workers can increase API load and log volume] → Mitigation: keep polling intervals configurable, log transitions separately from raw samples, and scope v1 watch features to terminals that require them.

[Manual operator interaction can still create ambiguous snapshots] → Mitigation: model external activity explicitly and keep raw observation separate from owned-work conclusions.

[CLI delegation can drift from CAO behavior across versions] → Mitigation: pin compatibility to the targeted CAO version and add delegated-command parity tests for the supported command family.

[Derived child port may conflict with an already-used `public_port + 1`] → Mitigation: fail startup explicitly when the derived child port cannot be bound; do not add a user-facing child-port override in this change.

[Introducing another server boundary adds runtime surface area] → Mitigation: keep v1 opt-in and limited to the routes and features needed for current Houmao interactive workflows.

## Migration Plan

1. Add `houmao-server` HTTP models, server runtime, child-CAO lifecycle management, persistence helpers, and a local entrypoint.
2. Implement CAO-compatible route mapping that dispatches most work to the child `cao-server` on the derived internal port `public_port + 1`, while keeping Houmao extension routes server-owned.
3. Add persistent per-terminal watch workers plus extension routes for Houmao-owned terminal state and history.
4. Extend `houmao-cli` with a CAO-compatible command family that delegates most commands to `cao` and registers launched live agents with `houmao-server`.
5. Add runtime start, inspect, prompt, control-input, interrupt, and stop flows for a new `houmao-server` REST-backed mode while leaving direct CAO flows intact.
6. Add tests and reference docs for server API compatibility, CLI compatibility, child-CAO lifecycle, watch behavior, and the migration path toward eventual CAO replacement.

Rollback is straightforward because the new server mode is opt-in. Existing direct CAO-managed sessions continue to function unchanged while `houmao-server` matures.

## Open Questions

None. The remaining work is implementation detail within the boundaries above.
