## Context

The mailbox reference tree already contains the exact contract material for the implemented Stalwart transport and the gateway `/v1/mail/*` surface, but that information is still hard to approach in the right order. The current shape leaves first-time readers to infer the intended workflow from a mix of filesystem-first quickstart guidance, low-level contract pages, and broader runtime references.

Three documentation problems now overlap:

- `docs/reference/mailbox/quickstart.md` and `docs/reference/mailbox/internals/runtime-integration.md` still present mailbox setup through a filesystem-first narrative even though `stalwart` is now a current transport.
- `docs/reference/gateway/index.md` and the gateway subtree explain queueing and lifecycle well, but they do not present the gateway mailbox facade as a first-class reader path.
- `docs/reference/system-files/agents-and-runtime.md` inventories runtime and gateway artifacts, but it does not clearly explain the Stalwart secret lifecycle boundary between secret-free manifests, durable credential references, and session-local materialized credential files.

This change is documentation architecture work, not runtime design work. The implementation already exists. The design problem is to make the existing behavior legible to two audiences without duplicating every contract page:

- first-time operators who need a safe path to their first Stalwart-backed session,
- developers and maintainers who need exact source-aligned boundaries for runtime, gateway, and filesystem responsibilities.

## Goals / Non-Goals

**Goals:**

- Create one clear operator-facing narrative for Stalwart-backed mailbox setup and first use.
- Create one clear gateway-facing narrative for the shared mailbox facade and how it interacts with Stalwart-backed or filesystem-backed sessions.
- Make the transport choice and the gateway-versus-direct mailbox path visible near the top of the mailbox docs instead of burying them in contract pages.
- Make the secret lifecycle explicit in the system-files docs so readers can tell what is persisted, what is durable runtime-owned state, and what is session-local secret material.
- Keep the detailed protocol shapes in the existing contract pages and use higher-level pages to route readers into those exact references.
- Preserve the existing mailbox, gateway, and system-files subtree boundaries instead of introducing a new top-level "Stalwart" documentation silo.

**Non-Goals:**

- No runtime, gateway, mailbox, or schema behavior changes.
- No standalone Stalwart server-administration manual for every possible deployment topology.
- No duplication of full payload schemas, HTTP examples, or manifest shapes across every new page.
- No reorganization of unrelated docs trees beyond the links and pages needed to make this reader path coherent.

## Decisions

### 1. Keep Stalwart documentation inside the existing mailbox and gateway trees

This change will not create a new top-level `docs/reference/stalwart/` subtree. Stalwart is part of the mailbox transport story, and the gateway mailbox facade is part of the gateway story.

Documentation ownership will stay split this way:

- `docs/reference/mailbox/`: operator path, mailbox transport comparison, runtime mailbox integration, and links to exact mailbox contracts.
- `docs/reference/gateway/`: the shared mailbox facade, gateway attachment context, loopback-only route availability, notifier behavior, and adapter boundaries.
- `docs/reference/system-files/`: runtime-owned filesystem placement, contract level, and secret lifecycle for persisted versus materialized artifacts.

Rationale:

- readers asking "how do I use Stalwart with Houmao?" are really asking a mailbox question first,
- readers asking "what does the gateway do with Stalwart-backed mail?" are asking a gateway question,
- a separate top-level Stalwart docs tree would force readers to learn a second information architecture for one transport.

### 2. Add two narrative pages and use existing contract pages as the exact reference layer

The documentation should gain two new pages:

- `docs/reference/mailbox/operations/stalwart-setup-and-first-session.md`
- `docs/reference/gateway/operations/mailbox-facade.md`

These pages should explain the system in prose first, then route readers to the exact contract pages for payloads and schema details.

The mailbox operator page should cover:

- what Houmao assumes about the available Stalwart endpoints and credentials,
- how `start-session --mailbox-transport stalwart` changes the runtime flow,
- what the runtime provisions or validates,
- how to verify the first session with `mail check`, `mail send`, and `mail reply`,
- when a live gateway mailbox facade becomes the preferred shared path.

The gateway mailbox page should cover:

- why `/v1/mail/*` exists as a shared mailbox facade,
- how the gateway resolves transport adapters from `attach.json` to `manifest.json`,
- how the same gateway surface serves both filesystem and Stalwart-backed sessions,
- why mailbox routes remain loopback-only for now,
- how notifier polling uses the same facade rather than transport-local side channels.

Rationale:

- the exact contract docs already exist and should stay the source of truth,
- what is missing is an intentional narrative path that tells readers which contract page matters next and why.

### 3. Use a two-lane reading path: first session first, deep contracts second

The updated docs should make reader intent explicit:

- lane 1: "I want to start a Stalwart-backed mailbox session and send or read mail safely."
- lane 2: "I need to debug or extend runtime, gateway, or storage behavior."

To support that split:

- `docs/reference/mailbox/quickstart.md` should become a short transport-selection page that points filesystem readers to the existing inline path and Stalwart readers to the new operations page.
- `docs/reference/mailbox/index.md` and `docs/reference/gateway/index.md` should highlight the new Stalwart and mailbox-facade pages in their "start here" path.
- `docs/reference/mailbox/internals/runtime-integration.md` should explain the full runtime flow from declarative config through manifest persistence, direct fallback, and gateway-backed shared operations.

Rationale:

- new readers should not need to open protocol pages first,
- developers still need a clear path from narrative pages into the exact contract pages without encountering contradictory framing.

### 4. Make responsibility and secret boundaries explicit with tables near the top of the new or updated pages

The docs should stop relying on readers to infer boundaries implicitly from prose. The new Stalwart-facing pages should include concise comparison tables near the top.

At minimum:

- a responsibility table for Houmao runtime versus gateway versus Stalwart,
- a transport comparison table for filesystem versus Stalwart,
- a persisted-versus-secret table that distinguishes manifest payloads, durable runtime-owned credential references, and session-local materialized secret files.

Rationale:

- this change is primarily about reducing confusion at subsystem boundaries,
- a small table is more effective than repeating the same distinction across multiple paragraphs.

### 5. Treat direct `mail` commands as the first onboarding path, then explain gateway preference

The first-time-user flow for Stalwart should start with one mailbox-enabled session and direct `mail check`, `mail send`, and `mail reply`. The docs should then explain that once a live gateway is attached, the runtime-owned mailbox guidance prefers the shared `/v1/mail/*` facade for mailbox operations that both transports support.

This means the docs will intentionally present:

1. start a Stalwart-backed session,
2. verify mailbox behavior directly,
3. understand the optional gateway mailbox facade and why it becomes the preferred shared path when present.

Rationale:

- this is the shortest path to a correct first success,
- it keeps gateway attachment optional in the onboarding flow while still documenting the preferred shared abstraction once the gateway exists.

### 6. Document Houmao-side assumptions about Stalwart, not a full generic Stalwart manual

The Stalwart operator page should document the assumptions Houmao needs:

- JMAP endpoint and management endpoint expectations,
- credential inputs and how the runtime stores references rather than inline secrets,
- what the runtime will provision or validate,
- the observable outcomes a Houmao operator should expect.

It should not try to become a full standalone Stalwart server deployment handbook.

Rationale:

- the repo needs an integration guide, not a replacement for Stalwart's own admin documentation,
- staying scoped to Houmao-observable requirements reduces drift and keeps the page maintainable.

### 7. Keep filesystem placement in the system-files tree and link out from mailbox and gateway pages

The system-files subtree should become the canonical place that explains where Stalwart-related runtime artifacts live and how they differ in contract strength.

`docs/reference/system-files/agents-and-runtime.md` should be expanded to cover:

- secret-free mailbox manifest persistence,
- durable runtime-owned credential references or stored material,
- session-local materialized credential files used by direct or gateway-backed access,
- the relationship between the mailbox binding in `manifest.json` and the actual secret-bearing files.

Mailbox and gateway pages should describe the semantics of those artifacts, but they should link to the system-files page when the reader needs the broader filesystem map.

Rationale:

- the system-files subtree already owns the filesystem inventory problem,
- mailbox and gateway docs should explain meaning without becoming a second filesystem map.

## Risks / Trade-offs

- [Risk] The new narrative pages could drift from the contract pages by paraphrasing too much detail. → Mitigation: keep exact payloads and schema shapes in the contract pages and have the new pages summarize and link rather than restate.
- [Risk] A new Stalwart operator page could accidentally become a generic server manual. → Mitigation: limit it to Houmao-side prerequisites, runtime behavior, and observable outcomes.
- [Risk] The gateway mailbox facade page could blur the distinction between loopback-only current behavior and future authenticated exposure. → Mitigation: make loopback-only availability an explicit current-scope section near the top.
- [Risk] Readers could still miss the secret lifecycle and assume the manifest stores passwords. → Mitigation: add a persisted-versus-secret table and reinforce it in both mailbox and system-files pages.
- [Risk] Updating quickstart to branch by transport could make the page feel heavier. → Mitigation: keep the quickstart page short, with a minimal decision point and direct links into the deeper Stalwart page.

## Migration Plan

1. Add the new Stalwart operator page under `docs/reference/mailbox/operations/`.
2. Add the new gateway mailbox-facade page under `docs/reference/gateway/operations/`.
3. Update mailbox entry and internals pages to route readers into the new narrative path and reflect direct-versus-gateway behavior clearly.
4. Update `docs/reference/system-files/agents-and-runtime.md` so the Stalwart secret lifecycle and runtime-owned artifact placement are explicit.
5. Update the relevant OpenSpec reference-doc specs so future doc changes have to preserve this reader path and these boundary explanations.

Rollback is straightforward because the change is documentation-only: remove the new pages, restore the previous links, and revert the spec deltas if the structure proves confusing.

## Open Questions

- Should `docs/reference/system-files/agents-and-runtime.md` document the exact on-disk naming convention for Stalwart credential files, or only the path family and contract level?
- Should the new Stalwart operator page include one minimal end-to-end example with gateway attached, or should gateway-attached flows remain entirely in the gateway subtree to avoid mixed focus?
