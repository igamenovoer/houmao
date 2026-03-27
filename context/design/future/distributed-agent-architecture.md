# Distributed Agent Architecture

## Purpose

This note records an intended future direction for Houmao:

- retire all CAO-facing functionality as a public product surface,
- stop treating server-backed TUI creation as a first-class user workflow,
- treat tmux-backed agents as the primary runtime substrate,
- make `houmao-server` optional rather than mandatory, and
- let `houmao-server`, when present, act as a coordination and discovery authority over already-running distributed agents rather than as the place where those agents must be created.

This is a future-architecture note, not a description of the current implementation.

## Core Intent

The system is moving toward a model where agents are fundamentally hosted in tmux-backed runtime sessions, and server presence is optional.

The desired operational story is:

1. An agent runs in a tmux session on some host.
2. That session publishes enough durable state to be resumed and enough registry state to be discoverable.
3. The agent may optionally expose a live gateway for queued prompt delivery, interruption, mailbox wake-up, and other shared-control behaviors.
4. `houmao-server`, if running, discovers those distributed sessions through the shared registry and exposes higher-level capabilities on top:
   - agent-name-based addressing
   - shared resource management
   - coordination between agents
   - shared communication patterns
   - optional centralized observation and state projection

In this model, the server is not the birthplace of the agent. It is an optional coordination plane over agents that can already exist independently.

## High-Level Model

```text
without server

houmao-mgr
  -> launch local runtime session
  -> create tmux-backed agent
  -> publish manifest + shared registry + optional gateway capability
  -> later commands resume from manifest/registry


with server

houmao-mgr / other clients
  -> talk to houmao-server
  -> houmao-server discovers live agents from shared registry
  -> houmao-server exposes agent-name-based addressing and coordination APIs
  -> houmao-server may attach to agent gateways, inspect state, and manage shared resources
```

The server remains useful, but it becomes useful as a coordinator, not as a required session-creation shim.

## Desired Role Of Runtime Sessions

Runtime sessions should be the durable substrate.

The durable reality of an agent should be:

- a session manifest,
- a tmux session,
- the provider TUI or headless runtime process,
- optional gateway artifacts,
- optional mailbox or shared-resource bindings,
- a shared live-agent registry record.

The in-memory Python objects used by `houmao-mgr` should remain ephemeral wrappers around that durable substrate. They are not the long-term owner of the session.

This direction is already closer to how local runtime-backed sessions behave today:

- a launch command constructs controller objects,
- those objects bring up or resume tmux-backed runtime state,
- then the CLI process exits,
- later commands reconstruct controller objects from persisted state.

That pattern is a better fit for a distributed architecture than a model where all important session identity has to originate from a resident server process.

## Desired Role Of Agent Gateways

The gateway concept remains useful in this future.

The gateway should be treated as an optional live control facade layered on top of a running agent session. It is not the agent itself.

A gateway may provide:

- queued prompt admission,
- interrupt delivery,
- mailbox wake-up integration,
- shared coordination hooks,
- richer live execution state,
- a synchronization point for multi-agent orchestration.

In this future, a tmux-backed session may exist in three broad states:

```text
tmux-backed agent only
  session exists
  manifest exists
  registry exists
  no live gateway

tmux-backed agent + gateway-capable metadata
  session exists
  attach contract exists
  no gateway process currently attached

tmux-backed agent + live gateway
  session exists
  gateway is attached
  queued control and coordination features are active
```

The existence of the gateway should not be required for the existence of the agent.

## Why Retire CAO As A Public Surface

The current repository still carries significant CAO-era compatibility structure:

- `/cao/*` endpoints on `houmao-server`
- `cao_rest` runtime backend
- `houmao_server_rest` runtime backend
- registration flows that bridge CAO-created sessions into the managed-agent API
- demo packs and docs that still describe CAO-compatible session creation as canonical

The intent behind retiring CAO is not that tmux-backed TUI agents are unimportant. The opposite is true.

The intent is that the CAO-specific server-creation layer no longer appears necessary as the primary architecture for the product we now want.

The current reasoning is:

- we do not currently have a compelling product use case for server-based tmux session creation,
- we do want local or distributed tmux-backed agents that exist independently of server lifetime,
- we do want a shared server coordination plane when useful,
- and we do not want long-term architecture to stay constrained by CAO compatibility if that compatibility no longer serves a real product direction.

So the planned posture is:

- retire all CAO functionality as a supported public product capability,
- keep code temporarily where needed for transition or internal compatibility,
- but fail explicit public attempts to use CAO creation paths.

## Why `houmao_server_rest` Stops Making Sense As A Public Creation Path

`houmao_server_rest` represents a server-backed TUI session model.

In the current design, it mainly exists because the server:

- creates a TUI session through a CAO-compatible path,
- persists a server-owned registration record,
- tracks and addresses the session as a managed agent.

If the future design instead says:

- agents are primarily launched as local or distributed runtime sessions,
- those sessions publish themselves through the shared registry,
- `houmao-server` discovers and coordinates them later,

then the need for a public server-backed TUI-creation backend becomes much weaker.

At that point, `houmao_server_rest` largely becomes a legacy transport identity for an older admission model rather than a feature that users should still be encouraged to create.

This does not mean all server-managed concepts disappear.

It means the creation authority shifts:

- from server-created TUI sessions
- toward registry-discovered distributed TUI sessions

That is a meaningful architecture change.

## Target Public Model

The intended public model should look roughly like this.

### Agent existence

Agents exist because a runtime session exists.

That runtime session may be:

- local interactive TUI,
- local headless,
- remote but registry-visible tmux-backed TUI,
- remote but registry-visible headless session.

### Server optionality

If no server is running:

- agents can still be launched,
- agents can still be addressed locally,
- gateways may still be attached,
- the system still functions as a local runtime tool.

If a server is running:

- it discovers the agents,
- it can expose stable names and higher-level APIs,
- it can coordinate communication and shared resources,
- it can present centralized state and control surfaces.

### Naming and addressing

The server should primarily provide:

- agent-name-based addressing,
- possibly aliases or group names,
- coordination-friendly identity layers above raw tmux session names or raw agent ids.

This is especially important if agents are distributed across multiple tmux sessions and possibly multiple hosts in the future.

### Shared resource management

The server should be able to coordinate resources that do not belong naturally to one single agent process, such as:

- mailbox or message-routing policies,
- shared file-backed or memory-backed coordination state,
- resource locks or leases,
- global registries of live capabilities,
- bounded concurrency or execution admission,
- future multi-agent workflow artifacts.

### Inter-agent communication

One desired future role for the server is agent coordination.

That may include something like synchronous or near-synchronous communication between agents, for example:

- request-response RPC-like exchanges,
- bounded task delegation,
- mailbox-like asynchronous handoff,
- live gateway-mediated wake-up,
- explicit orchestration barriers or rendezvous,
- future shared conversation or coordination channels.

The exact protocol is not fixed in this note. The important point is that server value should come from coordination, not from being the place where every TUI had to be born.

## Proposed Retirement Direction

The intended retirement direction is:

1. Disable all `/cao/*` public endpoints as supported user-facing functionality.
2. Disable public creation of `houmao_server_rest` sessions.
3. Keep the underlying code for a transition period if that reduces migration risk.
4. Return explicit, intentional errors for retired public creation paths.
5. Move server discovery and managed-agent authority toward shared-registry-based admission.

This implies:

- `/cao/*` is no longer a supported compatibility namespace,
- `houmao-server register-launch` is no longer a supported public creation bridge,
- `/houmao/launches/register` is no longer a supported public creation bridge,
- docs and demo packs should stop presenting CAO-compatible creation as a normative workflow.

## Important Distinction: Route Removal Vs Authority Refactor

There are two very different kinds of change hiding under the phrase "disable CAO."

### Surface-level route retirement

This means:

- return errors from `/cao/*`,
- return errors from launch-registration routes,
- stop documenting those workflows.

That part is straightforward.

### Authority-model change

This means:

- changing how `houmao-server` decides which TUI sessions are "real" managed agents,
- changing what seed data the TUI tracking system trusts,
- changing stop/addressing assumptions for distributed sessions,
- changing what it means for the server to "own" a session.

That part is the deeper change.

Current server TUI tracking is registration-backed.

The current implementation seeds known TUI sessions from server-owned registration records and uses shared-registry records only as enrichment. The future intent described here points the opposite direction:

- shared registry becomes primary discovery/admission evidence,
- server-owned registration becomes unnecessary for normal distributed agents.

That is a meaningful architectural refactor and should be treated as such.

## Current Architecture Assumptions That This Future Intends To Change

### 1. `houmao-server` currently presents itself as a CAO-compatible authority

Current specs and docs describe `houmao-server` as exposing the full `/cao/*` compatibility surface.

This future direction rejects that as a long-term public identity.

### 2. Current server-managed TUI admission is registration-backed

Today, TUI sessions are admitted into server tracking through:

- creation on `/cao/*`, and
- registration on `/houmao/launches/register`.

This future direction intends to replace that with shared-registry-driven discovery.

### 3. `houmao_server_rest` is currently treated as a real public runtime identity

Current runtime artifacts, manifests, demos, and tests explicitly use `backend = "houmao_server_rest"`.

This future direction treats that backend as a legacy or transitional construction path rather than something users should create going forward.

### 4. Several docs and demos still assume CAO-backed TUI creation is canonical

That assumption will no longer be valid under this future direction.

## Impact Analysis

The impact of this refactor is broad.

It is not limited to route handlers.

### Public API impact

If all `/cao/*` endpoints are disabled:

- the current `houmao-server` compatibility contract is intentionally broken,
- any client or demo still depending on CAO-compatible creation or control will fail,
- `houmao-server` should stop being documented as a CAO-compatible HTTP authority.

If `/houmao/launches/register` is disabled:

- the public bridge that turns CAO-created TUI sessions into managed agents disappears,
- all workflows built around "create then register" must be retired or replaced.

### Server tracking impact

Today the server's TUI tracking entrypoint is registration-based.

If public registration is retired, the server needs a new admission authority.

That likely means:

- discovering candidate sessions from shared registry,
- validating they map to live tmux-backed agents,
- deciding whether every live registry record should be server-trackable,
- defining what constitutes safe server-owned control over a discovered distributed session.

This is the largest conceptual shift in the change.

### Runtime identity impact

The future architecture likely wants to reduce reliance on:

- `cao_rest` as a supported user-facing runtime backend
- `houmao_server_rest` as a supported public creation backend

Those backends may remain in code for a while, but they should stop defining the main public architecture story.

### CLI impact

Current `houmao-mgr agents launch` already does not use CAO for normal local launch.

That is aligned with the future direction.

The bigger CLI impact is around:

- any commands or docs that still imply `houmao-server` is the place to create TUI sessions,
- any server-side helper commands that still exist only to bridge CAO-created sessions into Houmao.

### Documentation impact

A large portion of current docs will need revision or retirement.

In particular, material that currently describes:

- `houmao-server` as a `/cao/*` compatibility authority,
- `houmao_server_rest` as a normal runtime path,
- CAO-backed interactive tutorial packs as canonical,

will become misleading.

### Demo-pack impact

Several demo packs are explicitly built around `cao_rest` or `houmao_server_rest`.

Those packs will need one of three outcomes:

1. retire the pack,
2. rewrite the pack around local or registry-first runtime sessions,
3. keep the pack as historical/internal transition material rather than current product guidance.

### Test impact

There is broad existing test coverage that assumes:

- `/cao/*` routes exist,
- launch registration exists,
- `houmao_server_rest` artifacts are generated,
- CAO-backed demo parameters are valid,
- server-managed TUI admission flows remain available.

This change will require a deliberate test migration, not just a few expectation edits.

## What Should Likely Stay

Even while retiring CAO functionality, several current ideas remain valuable and should be preserved.

### Shared registry

The shared live-agent registry remains useful as the discovery substrate for distributed agents.

This future direction increases its importance rather than reducing it.

### Durable manifests and session roots

Session manifests and runtime roots remain the durable substrate for runtime resume and inspection.

### Gateways

Gateway-capable and gateway-attached session concepts remain valuable.

### Managed-agent abstraction

Users should still be able to address agents by meaningful names rather than by raw tmux details.

### Optional server

Keeping `houmao-server` optional is a feature, not a fallback embarrassment.

This makes local workflows simpler and lets the server become a higher-value coordination layer.

## Risks And Design Questions

### 1. What admits a session into server management?

If shared registry becomes primary, what exact criteria admit a session into server-managed discovery and tracking?

Options include:

- every fresh registry record,
- only records with valid tmux liveness,
- only records with explicit opt-in metadata,
- only records under an allowed runtime root or trust domain.

This question matters because it defines the trust and ownership boundary.

### 2. What does server-owned stop mean for registry-discovered sessions?

If the server did not create the session, is it still allowed to stop it?

This may be acceptable, but it needs an explicit contract rather than inherited assumptions from server-owned registration.

### 3. How should shared-resource coordination be modeled?

If the server is a resource and communication coordinator, do those resources remain filesystem-authoritative, memory-primary, or hybrid?

Different resources may need different answers.

### 4. How much legacy code should remain live?

There is a difference between:

- keeping legacy code compiled but unreachable from public APIs,
- keeping legacy APIs alive but marked deprecated,
- removing code entirely.

This note assumes "keep code, disable public creation" as the initial retirement posture.

### 5. Should any `/cao/*` routes remain read-only during transition?

The intent recorded here says retire all CAO functionality.

That is coherent, but it is still worth recognizing that a transition plan could distinguish:

- full immediate retirement, or
- creation-path retirement first, read-only compatibility later.

This note records the stronger retirement intent, not the phased compromise.

## Suggested Migration Framing

The refactor should be framed as:

- retiring CAO compatibility as a public product surface,
- promoting registry-first distributed-agent discovery,
- making `houmao-server` an optional coordination and resource-management layer,
- de-emphasizing or retiring `houmao_server_rest` as a public creation model.

That is a cleaner story than saying only "disable some endpoints."

The endpoint changes are a consequence of the architecture decision, not the architecture decision itself.

## Expected Future Story For Users

The system should eventually be explainable like this:

```text
Launch agents wherever they belong.
They run in tmux-backed runtime sessions.
They may expose gateways.
They publish discovery state.

If you want local control only, use houmao-mgr directly.

If you want coordination, shared resources, stable names, cross-agent messaging,
or centralized observation, run houmao-server and let it discover the agents.
```

That is the architecture this note is trying to move toward.

## Summary

The intent recorded here is:

- retire all CAO functionality as a supported public Houmao capability,
- stop exposing public creation paths for `houmao_server_rest`,
- keep tmux-backed runtime sessions as the real agent-hosting substrate,
- make `houmao-server` optional,
- and reposition `houmao-server` as a discovery, coordination, naming, communication, and shared-resource authority over distributed agents rather than as a required TUI creation shim.

The impact is significant:

- public API contracts change,
- server TUI admission authority changes,
- specs, demos, docs, and tests need coordinated revision,
- and the architecture becomes more explicitly registry-first and distributed.

This is a coherent future direction, but it should be treated as an architecture refactor, not as a small compatibility cleanup.
