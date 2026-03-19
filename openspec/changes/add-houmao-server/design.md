## Context

Today, Houmao reaches interactive HTTP-backed sessions primarily through `cao-server` and the repo-owned `CaoRestClient`, and CAO-native operator workflows still depend on the `cao` CLI. That gives Houmao working server and CLI boundaries, but both are owned by CAO. Persistent state watching is either request-scoped inside `cao_rest` waits or implemented in demo-only monitor code. Features such as continuous watch workers, server-owned state history, and Houmao-specific terminal status still sit outside the main server boundary.

The new target is not a per-session sidecar. It is a first-party server process named `houmao-server`, conceptually parallel to `cao-server`, plus a CAO-compatible service-management CLI named `houmao-srv-ctrl`. In the shallow first cut, `houmao-server` can start and supervise a child `cao-server` subprocess and dispatch most HTTP-compatible work to it, while `houmao-srv-ctrl` can shell out to `cao` for most CAO-compatible CLI verbs. But the compatibility promise is pairwise: `houmao-server + houmao-srv-ctrl` together replace `cao-server + cao`. Mixed pairs are not a supported contract in this change.

Constraints:
- v1 must not require modifying CAO source code
- v1 should stay shallow and delegate most server and CLI work to CAO where that reduces implementation cost
- the public API must be fully compatible with the supported `cao-server` HTTP API so that work that succeeds against `cao-server` also succeeds against `houmao-server`
- the new CAO-compatible CLI plan must avoid overloading the existing `houmao-cli` and instead provide a separate service-management binary
- compatibility is defined for the paired deployment `houmao-server + houmao-srv-ctrl`, not for mixed pairings with raw `cao` or raw `cao-server`
- the runtime, manifest, gateway, and registry schemas must represent `houmao-server` explicitly rather than smuggling it through `cao_rest`
- Houmao-owned CLI tools introduced in this change should be implemented with Python `click`
- Python data models introduced in this change should use `pydantic` wherever practical so server, runtime, and compatibility payloads follow one consistent style
- Houmao-owned CLI command trees introduced in this change should be split across smaller modules rather than concentrated in one giant `.py` file
- parity claims must be pinned to one exact upstream CAO fork commit, not to a floating branch name
- the shallow-cut child `cao-server` port must not become a user-facing configuration contract
- any filesystem state required by the child `cao-server` must stay behind Houmao-owned roots rather than surfacing as a separate operator-facing CAO home contract
- the design must classify existing persistent directories into long-term filesystem-authoritative, transitional compatibility, and memory-primary ownership instead of treating every current artifact as equally canonical forever
- direct human interaction with the live TUI remains supported
- the resulting design must create a clean seam for replacing CAO later instead of baking CAO deeper into Houmao

## Goals / Non-Goals

**Goals:**
- Add a first-party `houmao-server` HTTP service that Houmao clients can target directly
- Preserve the full supported `cao-server` HTTP endpoint API so `houmao-server` can act as a real drop-in replacement of `cao-server`
- Add a CAO-compatible command surface to `houmao-srv-ctrl` so it can act as a drop-in replacement of `cao`
- Make `houmao-server + houmao-srv-ctrl` together a drop-in replacement of `cao-server + cao`
- Make `houmao_server_rest` a first-class persisted backend identity across runtime-owned schemas
- Move persistent TUI watching and terminal-state publication into `houmao-server`
- Keep Houmao-specific status and watch features as explicit server extensions rather than demo-only logic
- Expose Houmao-owned filesystem roots and hide child-CAO storage details behind them
- Establish a durable persistence boundary that says which current artifacts remain filesystem-authoritative by design, which stay on disk only as transitional compatibility data, and which should become `houmao-server` memory with compatibility mirrors
- Require delegated `houmao-srv-ctrl launch` to materialize Houmao-owned authoritative session artifacts that existing runtime, registry, gateway, and mailbox flows can point to
- Start with CAO-backed subprocess delegation while preserving a clean migration path to native Houmao-owned backend implementations

**Non-Goals:**
- Re-implementing most CAO behavior natively in the first implementation
- Supporting mixed-pair deployments such as `houmao-server + cao` or `cao-server + houmao-srv-ctrl`
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

### Decision 2: Match the full supported `cao-server` HTTP API and keep Houmao extensions additive

**Choice:** `houmao-server` matches the full public HTTP API of the supported `cao-server` version, preserving route paths, methods, request arguments, request bodies, response status codes, and response bodies closely enough that behavior which works against `cao-server` also works against `houmao-server`.

Houmao-specific features may extend existing compatibility routes only additively, such as by accepting additional optional request arguments or fields and returning additional optional response fields that do not break CAO-compatible clients. Houmao-specific features may also appear on additional new endpoints owned by `houmao-server`.

**Rationale:**
- Minimizes migration cost for existing Houmao REST usage patterns
- Makes the drop-in replacement claim concrete instead of subset-based
- Lets the new server replace CAO incrementally without forcing every caller to change at once
- Keeps Houmao-only behavior explicit while still allowing additive extensions where that is operationally useful

**Alternatives considered:**
- Invent a completely different API immediately: increases migration cost and delays adoption
- Allow arbitrary divergence on existing CAO routes: rejected because it breaks the drop-in replacement goal
- Hide Houmao features inside breaking changes to CAO-compatible payloads from day one: makes compatibility and evolution harder to reason about

### Decision 2A: Define compatibility as a paired replacement, not independent crosstalk

**Choice:** The supported compatibility story in this change is the paired replacement `houmao-server + houmao-srv-ctrl` for `cao-server + cao`.

`houmao-server` is not required to support arbitrary external `cao` clients as a public contract, and `houmao-srv-ctrl` is not required to support arbitrary external `cao-server` deployments as a public contract. Mixed pairs such as `houmao-server + cao` and `cao-server + houmao-srv-ctrl` are explicitly unsupported.

**Rationale:**
- Keeps the compatibility promise coherent and testable
- Avoids accidental commitment to extra cross-product combinations that are not part of the intended migration path
- Lets Houmao add paired behaviors such as registration, discovery, and future query surfaces without pretending those behaviors exist in raw CAO components

**Alternatives considered:**
- Treat server and CLI compatibility as fully independent: rejected because it silently expands the supported matrix and makes parity harder to define
- Allow mixed pairs informally without testing them: rejected because users would reasonably interpret that as a support promise

### Decision 3: In v1, `houmao-server` starts and supervises a child `cao-server` subprocess

**Choice:** `houmao-server` manages one child `cao-server` subprocess in the shallow cut. Most CAO-compatible HTTP routes dispatch inward to that child server rather than re-implementing CAO logic immediately. The child CAO port is derived mechanically as `houmao-server` port `+1`, and no user-facing interface may override it independently.

If the child `cao-server` needs a `HOME` or any other on-disk support state, `houmao-server` provisions that storage inside a Houmao-owned server home or runtime-root subtree. Callers are not asked to provide, inspect, or reason about a separate CAO-branded home path.

Direct traffic to the child CAO endpoint is treated as an unsupported user or debug hack rather than as a supported public surface, even though a caller who already knows the internal port can technically still reach it.

**Rationale:**
- Keeps v1 shallow and practical
- Preserves a simple drop-in story for callers while Houmao grows server-owned features around the child
- Avoids forcing Houmao to hide or rewrite every existing CAO integration point in one change
- Keeps the filesystem mental model Houmao-centric instead of leaking a second CAO-branded home contract
- Prevents the internal child-port choice from hardening into another long-lived public contract

**Alternatives considered:**
- Embed CAO as a library: tighter coupling and a less realistic migration seam
- Proxy to an externally managed CAO only: weaker lifecycle ownership for the Houmao server
- Let operators choose an arbitrary child CAO port: rejected because it turns an internal shallow-cut detail into a public configuration surface
- Expose a child CAO home path or CAO-specific home override to users: rejected because it leaks an internal adapter detail into the long-term Houmao architecture
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

### Decision 4A: Make `houmao_server_rest` a first-class persisted backend identity

**Choice:** Runtime-owned sessions that talk to `houmao-server` use an explicit backend kind named `houmao_server_rest`.

That backend gets dedicated persisted contract sections rather than reusing `cao_rest` shapes:

- session manifests use a dedicated `houmao_server` section that stores the public `houmao-server` transport identity such as base URL plus server session and terminal identity
- gateway attach contracts gain `houmao_server_rest` backend support plus dedicated `houmao_server` backend metadata
- shared-registry identity records publish `backend='houmao_server_rest'` when they refer to those sessions

Child-CAO adapter details remain internal server state and do not become part of the runtime-owned persisted backend identity.

**Rationale:**
- The repo already enforces strict backend-discriminated manifest, gateway, and registry schemas
- Reusing `cao_rest` would keep the durable truth CAO-shaped even though `houmao-server` is the public authority
- A first-class backend identity keeps the future replacement seam honest and discoverable

**Alternatives considered:**
- Reuse `cao_rest` and overload existing CAO fields: rejected because it makes persisted artifacts semantically misleading
- Keep the backend identity implicit and infer it from incidental fields: rejected because the current schema model is explicit and strict

### Decision 5: Use `houmao-srv-ctrl` as the CAO-compatible service-management CLI and keep `houmao-cli` separate

**Choice:** This change introduces a dedicated binary named `houmao-srv-ctrl` for the CAO-compatible service-management surface and leaves the existing `houmao-cli` role unchanged. For the supported `cao` version, `houmao-srv-ctrl` is intended to be a real drop-in replacement for `cao` within the supported `houmao-server + houmao-srv-ctrl` pair, so aliasing `cao` to `houmao-srv-ctrl` should work for the supported command family. In the shallow cut, most CAO-compatible commands delegate to the installed `cao` executable and preserve CAO-facing behavior as closely as practical.

**Rationale:**
- Respects the existing role and user expectations around `houmao-cli`
- Gives service-management compatibility its own clean binary boundary
- Makes the operator story simple: alias `cao` to `houmao-srv-ctrl` and continue using CAO-native command habits
- Keeps the support matrix bounded to the intended Houmao-managed pair instead of promising arbitrary mixed crosstalk
- Keeps the shallow cut pragmatic by delegating most CLI behavior to the already-installed `cao`
- Creates a place to add Houmao-owned CLI-side behavior without waiting for full native replacement

**Alternatives considered:**
- Overload `houmao-cli` with CAO compatibility: rejected because `houmao-cli` already exists for different responsibilities
- Add a differently named wrapper with no drop-in story: rejected because aliasing `cao` to the Houmao binary should just work
- Re-implement the whole `cao` CLI immediately inside Houmao: too much scope for v1

### Decision 5A: Implement Houmao-owned CLI tools in this change with Python `click` and modular command modules

**Choice:** Houmao-owned CLI tools introduced in this change, especially `houmao-srv-ctrl` and the local `houmao-server` entrypoint, should be implemented with Python `click`.

The command trees for those CLIs should be decomposed across smaller command modules rather than collected into one giant `.py` file.

This is an implementation-style choice rather than a public compatibility contract. The public contract is still CAO-compatible behavior for the supported pair, not the internal Python CLI framework.

**Rationale:**
- Gives the new Houmao CLIs one consistent command-tree and option-parsing style
- Fits well with nested subcommands, help generation, and explicit option validation
- Keeps the CLI implementation straightforward while the command surfaces are still evolving
- Makes individual command families easier to read, test, and extend without turning the compatibility wrapper into one oversized module

**Alternatives considered:**
- `argparse`: workable, but less ergonomic for the multi-command CLI surfaces in this change
- `typer`: viable, but `click` is the explicit implementation choice for this change
- ad hoc shell wrappers around Python modules: too brittle for the compatibility and verification requirements here
- one giant `click` module with every command in one file: rejected because it scales poorly once compatibility wrappers and Houmao-only extensions accumulate

### Decision 5B: Use `pydantic` for new data models wherever practical

**Choice:** New Python data models introduced in this change should use `pydantic` wherever practical.

This applies especially to:

- `houmao-server` HTTP request and response models
- Houmao-owned terminal state and history payloads
- persisted compatibility or runtime-facing payload models introduced by this change
- structured CLI-to-server registration or extension payloads

This is an implementation-style consistency choice rather than a separate public wire contract. It does not require rewriting every pre-existing non-`pydantic` model in the repository inside this change.

**Rationale:**
- Keeps new server, runtime, and compatibility payload definitions on one consistent validation and serialization model
- Fits the repo's need for explicit structured contracts across HTTP, persistence, and CLI integration points
- Reduces the chance that different parts of the new server stack drift into incompatible ad hoc payload handling

**Alternatives considered:**
- Mix `dataclass`, handwritten dict validation, and `pydantic` freely: rejected because it weakens consistency across a contract-heavy change
- Rewrite all existing repo models to `pydantic` in the same change: rejected because it would over-scope the implementation

### Decision 6: Register CAO-compatible launch results into `houmao-server`

**Choice:** For CAO-compatible CLI flows that create or launch a live agent session, `houmao-srv-ctrl` performs the delegated CAO operation first and then registers the resulting live agent or session with `houmao-server`.

For v1, `launch` is the minimum required registration hook.

**Rationale:**
- Lets operators keep CAO-native launch habits through `houmao-srv-ctrl` while Houmao-server gains awareness of the resulting live sessions
- Avoids requiring every live agent to be created only through the server HTTP path on day one
- Keeps the registration seam explicit for eventual native replacement

**Alternatives considered:**
- Register nothing on CLI launch: leaves server-owned watch/state blind to CLI-created sessions
- Force all launches through `houmao-server` only: not a drop-in CAO CLI story

### Decision 6A: Delegated `houmao-srv-ctrl launch` materializes Houmao-owned authoritative session artifacts

**Choice:** After delegated `cao launch` succeeds, `houmao-srv-ctrl` materializes Houmao-owned session artifacts for the launched session instead of leaving the launch server-only.

In v1, that means at minimum:

- create or update a Houmao runtime-owned session root
- write a runtime-owned manifest that uses `backend='houmao_server_rest'`
- let `houmao-server` registration reference that same authoritative session identity
- when transitional shared-registry publication is used, point registry runtime pointers back to that Houmao-owned manifest and session root
- let gateway and mailbox follow-up flows keep using manifest-backed authority through those artifacts while those subsystems still depend on runtime-owned manifests

**Rationale:**
- Current name resolution, gateway attach, and mailbox notifier support all depend on runtime-owned manifest pointers
- A paired replacement story is not operationally coherent if CLI-launched sessions follow a different authority model from runtime-launched sessions
- This approach preserves the repo's pointer-oriented design while keeping the long-term authority Houmao-owned

**Alternatives considered:**
- Server-only registration for delegated launches: rejected because it creates a second incompatible authority model
- Scope CLI-launched sessions out of registry/gateway/mailbox compatibility in v1: rejected because it weakens the paired replacement claim too much

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

### Decision 9: Classify persistent artifacts into filesystem-authoritative, transitional compatibility, and memory-primary state

**Choice:** `houmao-server` explicitly classifies current persistence into three buckets.

Filesystem-authoritative artifacts remain canonical on disk even in the long-term architecture. `houmao-server` may index or cache them, but it does not replace them as the source of truth. In v1, that bucket includes:

- runtime home roots and manifests such as `~/.houmao/runtime/homes/<home-id>/` and `~/.houmao/runtime/manifests/<home-id>.yaml`
- durable runtime session roots, especially `<runtime-root>/sessions/<backend>/<session-id>/manifest.json`
- mailbox storage under `~/.houmao/mailbox/...`
- workspace-local job directories such as `<working-directory>/.houmao/jobs/<session-id>/`
- Houmao-owned server roots
- log files

Transitional compatibility artifacts remain on disk in v1, but they are not intended to stay filesystem-authoritative forever. The main case in this change is the shared registry under `~/.houmao/registry/live_agents/<agent-id>/record.json`. In the shallow cut, `houmao-server` still reads and preserves those records on disk, but the intended long-term discovery contract is that agents and tools find each other through `houmao-server` query APIs rather than by treating raw registry files as the architectural center.

Opaque child-adapter storage may also exist on disk in v1, but it lives under Houmao-owned server roots rather than as a separate public CAO-home contract. The main case is child `cao-server` support state such as its effective `HOME` and adapter-private files. Those artifacts may be required operationally, but their detailed layout and contents are internal implementation detail rather than part of the user-facing filesystem design.

Memory-primary artifacts are live control-plane state that should move under `houmao-server` ownership. During migration, the server may still emit filesystem mirrors for compatibility, debugging, or operator inspection, but those files are no longer the canonical control-plane truth once the server owns them. In v1, that bucket includes:

- gateway-like live state under `<session-root>/gateway/`, especially `state.json`, `queue.sqlite`, `events.jsonl`, `run/current-instance.json`, and `run/gateway.pid`
- generated attachment/config views such as `<session-root>/gateway/attach.json` and `<session-root>/gateway/desired-config.json`
- child-adapter launcher bookkeeping under Houmao-owned server roots, especially pid, ownership, and last-launch-result artifacts

**Rationale:**
- Runtime manifests, mailbox, and job roots are durable content or tool-owned state by design rather than hot in-memory control state
- The shared registry is useful as a current compatibility bridge, but the intended future architecture is server-query-based discovery rather than permanent filesystem-first agent lookup
- Gateway-like queue, pid, and current-instance artifacts describe what is live right now and fit naturally under a resident server authority
- Child-CAO-required files may still exist on disk, but keeping them under Houmao-owned roots prevents those internal adapter details from becoming user-facing CAO-home contracts
- Child-launch bookkeeping should become part of Houmao's live supervision memory even if compatibility files still exist
- This prevents future `houmao-server` adoption from accidentally freezing every temporary compatibility file into a permanent architectural contract

**Alternatives considered:**
- Keep all current filesystem artifacts authoritative forever: simpler initially, but it preserves the wrong authority boundary for live server state
- Move nearly everything into memory: would fight the existing durable filesystem contracts for mailbox, manifests, and tool-owned working data while also over-scoping the first registry migration

### Decision 10: Pin v1 CAO parity to one exact tracked fork commit

**Choice:** The compatibility source of truth for this change is pinned to the tracked CAO fork checkout at:

- repository: `https://github.com/imsight-forks/cli-agent-orchestrator.git`
- commit: `0fb3e5196570586593736a21262996ca622f53b6`
- local tracked checkout: `extern/tracked/cli-agent-orchestrator`

Parity verification for both `houmao-server` and `houmao-srv-ctrl` is defined against that exact source rather than against a floating branch name such as `hz-release`.

**Rationale:**
- Full compatibility claims need one concrete oracle
- The repo already carries a tracked local checkout that can serve as that oracle
- Using an exact commit keeps parity verification reproducible and reviewable

**Alternatives considered:**
- Keep compatibility pinned only to a floating branch name: rejected because it is not stable enough for full parity claims
- Treat whatever `cao` happens to be on `PATH` as the contract: rejected because it makes verification non-deterministic

## Risks / Trade-offs

[A shallow CAO-backed first cut could become a permanent proxy layer] → Mitigation: keep the child-process and upstream-adapter boundaries explicit and keep CAO details out of public Houmao contracts.

[Full CAO compatibility may constrain API evolution] → Mitigation: keep compatibility pinned to the exact tracked `cao-server` source of truth, allow only additive extensions on existing routes, and move non-compatible behavior onto new Houmao-owned endpoints.

[Continuous watch workers can increase API load and log volume] → Mitigation: keep polling intervals configurable, log transitions separately from raw samples, and scope v1 watch features to terminals that require them.

[Manual operator interaction can still create ambiguous snapshots] → Mitigation: model external activity explicitly and keep raw observation separate from owned-work conclusions.

[HTTP compatibility can drift from CAO behavior across versions] → Mitigation: pin compatibility to `https://github.com/imsight-forks/cli-agent-orchestrator.git@0fb3e5196570586593736a21262996ca622f53b6` and add parity verification that exercises the same endpoint calls against both servers within the supported Houmao pair.

[CLI compatibility can drift from CAO behavior across versions] → Mitigation: pin compatibility to `https://github.com/imsight-forks/cli-agent-orchestrator.git@0fb3e5196570586593736a21262996ca622f53b6` and add parity verification that exercises the same commands against both `cao` and `houmao-srv-ctrl` within the supported Houmao pair.

[Users may assume mixed-pair crosstalk is supported] → Mitigation: state explicitly that only `houmao-server + houmao-srv-ctrl` is in contract, treat mixed pairs as unsupported, and avoid claiming parity coverage for those combinations.

[Derived child port may conflict with an already-used `public_port + 1`] → Mitigation: fail startup explicitly when the derived child port cannot be bound; do not add a user-facing child-port override in this change.

[Filesystem mirrors and transitional registry files could be mistaken for the authoritative control plane after `houmao-server` adoption] → Mitigation: classify filesystem-authoritative, transitional-compatibility, and memory-primary artifacts explicitly, keep generated compatibility views clearly marked, and move agent discovery toward `houmao-server` query surfaces instead of raw filesystem lookup.

[Introducing another server boundary adds runtime surface area] → Mitigation: keep v1 opt-in and limited to the routes and features needed for current Houmao interactive workflows.

## Migration Plan

1. Add `houmao-server` HTTP models, server runtime, child-CAO lifecycle management, persistence helpers, and a local entrypoint, including an explicit classification of filesystem-authoritative, transitional compatibility, and memory-primary artifacts.
2. Extend runtime-owned schemas with a first-class `houmao_server_rest` backend, dedicated manifest sections, dedicated gateway attach metadata, and registry identity/runtime pointers that keep child-CAO details out of the public persisted contract.
3. Implement full supported `cao-server` API route mapping that dispatches most work to the child `cao-server` on the derived internal port `public_port + 1`, while keeping Houmao extensions additive and compatibility-safe.
4. Add persistent per-terminal watch workers plus new Houmao-owned endpoints and additive compatibility-safe response or request extensions for terminal state and history, with live control-plane state owned in server memory.
5. Keep filesystem-authoritative artifacts in place, continue reading and writing shared registry files as a transitional bridge in v1, but move the architectural discovery direction toward future `houmao-server` query endpoints.
6. Emit gateway-like and child-launcher filesystem mirrors only as compatibility, debug, or migration views where needed.
7. Add `houmao-srv-ctrl` as a CAO-compatible command family that delegates most commands to `cao`, materializes Houmao-owned session roots and manifests for delegated launches, and registers those launched live agents with `houmao-server`, while leaving `houmao-cli` outside that compatibility surface.
8. Add runtime start, inspect, prompt, control-input, interrupt, and stop flows for a new `houmao-server` REST-backed mode while leaving direct CAO flows intact.
9. Pin parity verification to `https://github.com/imsight-forks/cli-agent-orchestrator.git@0fb3e5196570586593736a21262996ca622f53b6` and add tests/reference docs for full server API compatibility, additive extension safety, full `cao` CLI compatibility through `houmao-srv-ctrl`, explicit mixed-pair exclusion, child-CAO lifecycle, watch behavior, persistence-boundary migration, and the path toward eventual CAO replacement.

Rollback is straightforward because the new server mode is opt-in. Existing direct CAO-managed sessions continue to function unchanged while `houmao-server` matures.

## Open Questions

None. The remaining work is implementation detail within the boundaries above.
