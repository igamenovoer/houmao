## Context

`houmao-server` already exposes a transport-neutral managed-agent read API and native headless lifecycle routes, but those surfaces are still incomplete for the long-term official model.

Today:

- TUI agents have a rich server-owned live state model under terminal-keyed routes.
- Headless agents only expose coarse managed-agent state plus headless turn resources.
- Native headless launch already reuses the runtime session system, including mailbox bootstrap from manifest-backed launch plans.
- Stable gateway attach metadata already models tmux-backed headless sessions.
- Live gateway attach and execution still stop at the REST-backed subset, so headless sessions are not yet official first-class gateway targets.

That leaves an architectural gap:

- users can inspect TUI agents richly, but headless inspection is shallow;
- gateway wake-up is implemented as a runtime-local facility rather than a first-class managed-agent capability in `houmao-server`;
- headless gateway execution risks bypassing server-owned turn authority unless the callback path is defined carefully.

This change is not about baking ping-pong conversation behavior into the server. The server should provide the official managed-agent, gateway, and state contracts that make async mailbox-driven agent workflows supportable for demos and real automation.

## Goals / Non-Goals

**Goals:**

- Make queryable headless state part of the official managed-agent contract.
- Preserve a cheap transport-neutral managed-agent summary state while adding a richer detail surface.
- Make `houmao-server` the official control plane for managed-agent execution and gateway operations.
- Ensure gateway execution against server-managed headless agents flows through server-owned authority and persisted turn bookkeeping.
- Extend the runtime gateway subsystem so tmux-backed headless sessions can publish and attach live gateways through the same durable gateway path as other gateway-capable sessions.
- Keep mailbox and gateway status visible enough for async wake-up workflows to be inspected and automated.

**Non-Goals:**

- Implement ping-pong orchestration, round counting, or agent conversation policy inside `houmao-server`.
- Replace the existing TUI terminal-keyed live state route as the canonical raw TUI inspection surface.
- Proxy the full `/v1/mail/*` gateway mail facade through `houmao-server` in this change.
- Redefine unread or read state ownership away from the mailbox transport.
- Eliminate the existing headless `/turns` route family in this change.

## Decisions

### 1. Managed-agent state will have summary and detail layers

The existing `GET /houmao/agents/{agent_ref}/state` route will remain the transport-neutral summary surface. It should stay cheap, stable, and useful for orchestration. This route will grow redacted gateway and mailbox summary fields so callers can answer “is this agent gateway-enabled and mailbox-enabled?” without switching surfaces.

A new managed-agent detail route will be added for transport-specific inspection. The detail contract will be a discriminated union keyed by transport.

Why:

- summary state is already useful and should not become a heavyweight inspection route;
- TUI and headless do not share the same rich observables, so a transport-specific detail surface is more honest than forcing everything into one flattened shape.

Alternative considered:

- Put all rich detail onto the existing `/state` route.
  Rejected because it would bloat the common surface, create unstable optional fields, and blur the difference between orchestration state and deep inspection.

### 2. Headless detail will be execution-centric, not UI-centric

Headless agents will not pretend to have a parsed TUI surface. Their detailed state will instead model:

- runtime/controller resumability,
- tmux liveliness,
- current admission or execution posture,
- active turn metadata,
- last-turn detail and error evidence,
- mailbox summary,
- gateway summary,
- diagnostics.

This gives users a first-class state model without fabricating prompt-area or parser concepts that only make sense for TUI sessions.

The detailed headless payload should reuse the same coarse `turn` and `last_turn` concepts already exposed on summary managed-agent state and extend them with headless-specific evidence such as started timestamps, terminal result artifacts, or interrupt-requested posture. Structured diagnostics should reuse the same diagnostics family already exposed on summary managed-agent state rather than introducing a second incompatible error schema. In server model terms, this should build on `HoumaoManagedAgentTurnView`, `HoumaoManagedAgentLastTurnView`, and `HoumaoErrorDetail` rather than inventing parallel model families.

Alternative considered:

- Mirror TUI `surface`, `parsed_surface`, and parser-oriented fields for headless.
  Rejected because headless tools have a defined execution contract and durable turn artifacts, not a visible UI contract.

### 3. `houmao-server` will gain a transport-neutral managed-agent request API

The server will add `POST /houmao/agents/{agent_ref}/requests` as a managed-agent request submission surface. That surface will accept at minimum:

- `submit_prompt`
- `interrupt`

Accepted requests will return one transport-neutral accepted-request envelope for both request kinds. That envelope should carry a server-owned request identity, the accepted request kind, explicit admission detail, and optional headless-turn linkage when prompt submission creates a new headless turn.

For native headless agents, `submit_prompt` will be backed by the existing server-owned headless turn machinery and will return optional linkage to the created headless turn. The existing headless `/turns` family remains the durable headless detail surface, and this change does not add a second durable `/requests/{request_id}` resource.

For TUI-backed managed agents, the same request API will route to the transport-appropriate prompt or interrupt path.

Request validation and admission must be explicit:

- malformed or transport-incompatible typed request payloads return `422`,
- admission conflicts such as an already-active headless turn or reconciliation-required blocking return `409`,
- unavailable or recovery-blocked managed agents return `503`, and
- interrupt requests with no active interruptible work return an explicit transport-neutral no-op response rather than pretending an interrupt was delivered.

Why:

- the gateway needs one official callback surface for managed-agent execution;
- server-owned authority should remain centralized rather than forcing gateway code to know backend-specific control rules.

Alternative considered:

- Keep gateway execution backend-specific and have the gateway directly decide between CAO terminal APIs, local runtime headless logic, and server headless turn routes.
  Rejected because it spreads control authority across layers and makes managed-agent behavior depend on transport-private seams.

### 4. Server-owned gateway operations will be explicit managed-agent routes

`houmao-server` will expose managed-agent gateway routes for:

- attach,
- detach,
- status inspection,
- mail-notifier get/put/delete.

The live gateway remains a separate durable per-agent companion process with its own HTTP surface. The server routes act as the official managed-agent operating surface, while the gateway direct routes remain the execution and mailbox facade.

`POST /houmao/agents/{agent_ref}/gateway/attach` should be idempotent when a healthy live gateway is already attached for the same managed agent. In that case, the route returns the current gateway attachment or status rather than starting a second companion process. If persisted and live gateway state disagree or require reconciliation, the attach route should fail explicitly with conflict-style semantics instead of implicitly detaching and replacing the existing process.

Why:

- users and automation need one official place to operate managed agents;
- the gateway sidecar still needs to own its durable queue, local health, and mailbox facade.

Alternative considered:

- Move the entire gateway HTTP surface into `houmao-server`.
  Rejected because it would collapse the gateway’s durable per-agent control root into a centralized server concern and make later non-server runtime use harder.

### 5. Gateway execution will be refactored around adapter kinds, not only REST-backed terminals

The gateway execution layer will be split into adapter implementations:

- direct REST-backed terminal adapter for the existing `cao_rest` and `houmao_server_rest` runtime-owned sessions,
- local headless runtime adapter for runtime-owned headless sessions outside `houmao-server`,
- server-managed-agent adapter for server-owned managed-agent execution, especially native headless agents.

For server-managed agents, the gateway must call back into `houmao-server` rather than resuming the headless session locally. This preserves server-owned active-turn admission, persisted turn records, and interruption semantics.

At the implementation layer, the adapter boundary should be defined with a typed `Protocol`, consistent with the existing gateway mailbox adapter boundary and other behavioral interfaces in the repo. That remains below the normative spec boundary; the architectural requirement is the adapter behavior and selection seam, not a public class hierarchy.

Why:

- the runtime gateway subsystem must support both local runtime sessions and server-managed sessions;
- server-managed headless control must not be bypassed by a sidecar that privately resumes manifests.

Alternative considered:

- Use one local manifest-driven headless adapter everywhere.
  Rejected because it would split authority for server-managed headless agents and undermine durable turn control under `houmao-server`.

### 6. Native headless launch stays mailbox-focused; gateway lifecycle stays post-launch

The native headless launch request will remain focused on resolved launch inputs plus optional mailbox configuration. In this change, launch may accept:

- mailbox overrides, using the same conceptual resolution space as runtime session startup,

Gateway lifecycle remains a separate post-launch concern. A gateway can be launched later against the same tmux-backed agent session by using the published attach metadata, the tmux session environment, and the persisted manifest pointer for that session. The official server-owned gateway attach or detach routes remain the managed-agent control surface for that lifecycle.

Notifier enablement will remain a separate operational step rather than a launch-time identity field.

Blueprint or manifest-backed gateway listener defaults may still inform a later attach action, but they are not caller-supplied headless launch inputs in this change. Attach-time resolution should continue to reuse the runtime gateway seams such as `_resolve_gateway_listener` and capability publication rooted in `ensure_gateway_capability`, while launch-time resolution should reuse the existing mailbox seams such as `resolve_effective_mailbox_config` and `bootstrap_resolved_mailbox`.

Why:

- mailbox configuration is part of the official managed-agent launch contract and should not be forced back into manifest-private indirection;
- gateway startup is independently recoverable from attach metadata, so coupling it to agent launch would blur two different lifecycle boundaries and failure domains.

Alternative considered:

- Couple gateway startup and listener selection to the headless launch request.
  Rejected because the gateway can be launched later for the same live session, including from the same tmux session, by using session env and manifest-backed attachability. Making launch own gateway lifecycle would duplicate attach authority and turn gateway startup failures into agent-launch failures unnecessarily.

### 7. Existing TUI detail routes remain canonical; managed-agent detail will project them

The existing terminal-keyed TUI state route remains the canonical raw TUI inspection contract. The new managed-agent detail route for TUI agents will project key TUI state fields and include a reference to that canonical route rather than embedding the full raw TUI payload or redefining parser-specific semantics in a second incompatible shape.

Why:

- the TUI route already exists and is the best place for raw TUI-specific observation;
- managed-agent detail should unify discovery, not fork the TUI model.

Alternative considered:

- Create a second fully separate TUI detail model under managed-agent routes.
  Rejected because it would duplicate the TUI contract and create drift risk.

## Risks / Trade-offs

- [Two overlapping state surfaces can confuse callers] → Keep `/houmao/agents/{agent_ref}/state` explicitly summary-only and document the detail route as the transport-specific inspection surface.
- [Server and gateway status can drift if both try to own the same truth] → Keep durable gateway status and notifier truth in gateway-owned state, with server routes proxying or projecting that source rather than duplicating it.
- [Headless local runtime attach and server-managed attach need different control adapters] → Make adapter type an explicit architectural seam instead of hiding it behind backend conditionals.
- [Mailbox launch defaults and later gateway attach defaults can drift] → Keep mailbox resolution shared at launch time, and keep gateway listener resolution on the attach path where tmux session env and manifest-backed attach metadata are already authoritative.
- [Coupling gateway startup to agent launch would merge unrelated failure domains] → Keep gateway lifecycle explicit and post-launch so agent startup does not depend on immediate sidecar availability.
- [This work could accidentally become demo-shaped] → Keep conversation policy, round limits, and email content outside the server and treat the demo only as a downstream consumer of the contract.

## Migration Plan

1. Extend server models and responses with managed-agent summary additions and detailed-state payloads.
2. Add the managed-agent detail route and headless detail projection while keeping existing terminal routes unchanged.
3. Add the transport-neutral managed-agent request submission routes and back them with existing headless turn authority plus existing TUI control paths.
4. Add server-managed gateway lifecycle and notifier routes.
5. Refactor gateway execution into explicit adapter kinds and add server-managed-agent plus local-headless adapters.
6. Extend runtime live gateway attach support for tmux-backed headless sessions and rely on resume-time gateway-capability publication so existing runtime-owned sessions gain the new attach metadata when resumed rather than through a one-off migration path.
7. Update clients, docs, and demo helpers to consume the new official surfaces while keeping gateway lifecycle as a post-launch attach operation rather than a headless launch flag.

This change is additive. Existing coarse state routes, TUI terminal routes, and headless `/turns` routes remain valid during migration.

Rollback strategy:

- preserve the preexisting headless `/turns` family and TUI terminal state routes;
- keep gateway direct HTTP routes unchanged;
- gate new server-managed gateway and detail routes so they can be removed without corrupting durable runtime state if an implementation problem is found early.

## Deferred Follow-Up

- A later ergonomic change may decide whether `houmao-server` should proxy the gateway `/v1/mail/*` facade. This change explicitly keeps the split as “server controls gateway lifecycle, gateway serves mailbox operations.”
