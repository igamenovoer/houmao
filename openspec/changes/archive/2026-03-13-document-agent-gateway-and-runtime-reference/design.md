## Context

The runtime-managed agent model in this repo now spans several overlapping surfaces:

- high-level runtime and brain overviews in `docs/reference/brain_launch_runtime.md` and `docs/reference/agents_brains.md`,
- runtime lifecycle and public control entrypoints in `src/gig_agents/agents/brain_launch_runtime/cli.py`,
- persisted session state, resume logic, gateway-capability publication, and stop behavior in `src/gig_agents/agents/brain_launch_runtime/runtime.py`,
- strict gateway contracts in `src/gig_agents/agents/brain_launch_runtime/gateway_models.py`,
- gateway storage and tmux env publication in `src/gig_agents/agents/brain_launch_runtime/gateway_storage.py`,
- the live FastAPI sidecar and durable queue worker in `src/gig_agents/agents/brain_launch_runtime/gateway_service.py`,
- runtime and gateway error classes in `src/gig_agents/agents/brain_launch_runtime/errors.py`,
- behavior-defining regression tests such as `tests/unit/agents/brain_launch_runtime/test_gateway_support.py`.

The implementation has grown coherent enough that readers now need more than one overview page. First-time readers need a mental model of how runtime-managed sessions, direct prompt turns, raw control input, mailbox prompts, and queued gateway requests fit together. Developers and maintainers need exact interface contracts, file layouts, error boundaries, recovery rules, and current implementation scope without rediscovering them from code every time.

This change is cross-cutting because it introduces two new reference subtrees, updates top-level docs navigation, and refactors how existing runtime reference pages point to detailed documentation. The main design problem is documentation architecture rather than runtime architecture: we need a structure that is readable, source-aligned, and resistant to duplication.

## Goals / Non-Goals

**Goals:**

- Create a dedicated `docs/reference/agents/` subtree for runtime-managed agent concepts and runtime-owned interaction surfaces.
- Create a dedicated `docs/reference/gateway/` subtree for the agent gateway sidecar and its attach, status, queue, and recovery contracts.
- Separate intuitive orientation from exact contract detail so first-time readers and developers can use the same docs effectively.
- Make the agent and gateway docs explicitly traceable to implementation files and behavior-defining tests.
- Reduce duplication in broader runtime reference pages by turning them into entrypoints and link hubs rather than secondary deep references.
- Keep the new docs grounded in current implemented behavior, especially current v1 scope and unsupported paths.

**Non-Goals:**

- No runtime behavior change, protocol change, or API expansion.
- No attempt to document every helper function line-by-line.
- No merger of gateway docs into mailbox docs, even where the systems are adjacent in user workflows.
- No requirement to mirror the Python package layout exactly in the docs tree.
- No commitment to document deferred or future-facing behavior as if it were implemented now.

## Decisions

### 1) Create two dedicated reference subtrees rooted at reader intent

The documentation will be split into:

- `docs/reference/agents/`
- `docs/reference/gateway/`

Each subtree will use `index.md` as its entrypoint and organize detailed material by reader intent instead of by module name.

Rationale:

- the docs problem is not a lack of source material, but a lack of navigable structure,
- readers usually arrive with questions like “how does queued gateway control differ from direct prompt turns?” rather than “what does `runtime.py` do?”,
- a dedicated subtree gives room for growth without turning a single page into a catch-all reference.

Alternatives considered:

- Keep expanding `docs/reference/brain_launch_runtime.md`. Rejected because that page already mixes overview, CLI guidance, gateway notes, backend-specific notes, and session artifact details.
- Organize the docs directly around Python modules. Rejected because that would optimize for implementation familiarity instead of reference usability.

### 2) Use the same documentation layering pattern in both subtrees

Both the agent and gateway reference trees will separate detailed pages into:

- `contracts/`
- `operations/`
- `internals/`

The `index.md` page in each subtree will introduce the topic, key terms, and “read by goal” navigation.

Rationale:

- the mailbox reference already uses this pattern successfully and gives us a repo-local documentation precedent,
- the split maps cleanly to the kinds of questions readers bring,
- the same pattern across subtrees lowers cognitive overhead for future readers and maintainers.

Alternatives considered:

- Add only one page per subtree. Rejected because the content already spans too many distinct questions and audiences.
- Organize only by role such as operator versus developer. Rejected because the same person often needs both operational and architectural context in the same session.

### 3) Draw a strict subject boundary between agent docs and gateway docs

The `agents/` subtree will own runtime-managed session concepts:

- what a runtime-managed agent session is,
- how session identity, manifests, tmux targeting, and runtime storage work,
- what the main interaction paths are,
- how message passing differs across direct prompt turns, raw control input, mailbox prompts, and gateway-routed requests,
- what runtime-owned state and recovery boundaries look like.

The `gateway/` subtree will own gateway-specific concepts:

- gateway-capable versus gateway-attached sessions,
- attach contract and tmux env discovery,
- desired versus live listener state,
- HTTP routes and status payloads,
- durable queue and state artifacts,
- epoch, reconciliation, replay-blocking, and gateway-local health behavior.

Cross-links will be used whenever a page needs to reference the other subsystem rather than duplicating the same details twice.

Rationale:

- the runtime and gateway are closely related but not identical,
- duplication would make drift almost inevitable,
- readers need both a whole-system story and clear ownership for exact contract details.

Alternatives considered:

- Put all gateway material under `agents/`. Rejected because the gateway now has enough protocol and lifecycle detail to deserve its own dedicated reference home.
- Put all session lifecycle material under `gateway/`. Rejected because the gateway is optional and should not become the primary conceptual frame for all runtime-managed agent behavior.

### 4) Document current implementation first, then point to deferred behavior explicitly

The new docs will describe current implemented behavior as the primary contract. Where relevant, they will explicitly call out current v1 scope and non-goals, such as:

- gateway capability publication exists for runtime-owned tmux-backed sessions,
- live gateway attach is implemented first for `backend=cao_rest`,
- `GET /health` reports gateway-local health and does not imply managed-agent availability,
- queued gateway requests are durable but replay is blocked across managed-agent epoch changes,
- mailbox integration remains adjacent but independent from gateway behavior in v1.

The tests and source models will be treated as behavior anchors when docs wording needs to choose between “designed for” and “implemented today.”

Rationale:

- documentation is most useful when it matches what readers can observe and debug today,
- the gateway in particular has some intentional future extensibility, but the docs should not blur that into a claim of current support,
- source-aligned docs reduce confusion during implementation and review.

Alternatives considered:

- Write primarily from design intent or OpenSpec history. Rejected because several surfaces have already narrowed or clarified during implementation.
- Avoid mentioning deferred behavior entirely. Rejected because maintainers still need to understand where boundaries are intentional.

### 5) Use a consistent page pattern that teaches before it specifies

Each detailed page in either subtree should follow a shared writing rhythm:

1. short page-purpose statement,
2. mental model or plain-language framing,
3. exact technical details, contracts, or constraints,
4. concrete example, representative artifact shape, or walkthrough fragment where helpful,
5. embedded Mermaid `sequenceDiagram` block for important cross-component procedures,
6. source references.

Important terms should be introduced before they are used heavily, and pages should avoid assuming prior familiarity with internal jargon.

Rationale:

- the user goal here explicitly includes first-time readers and developers,
- “friendly but imprecise” would be a poor fit for debugging-oriented docs,
- a predictable shape makes it easier to review and maintain the docs over time.

Alternatives considered:

- Let each page evolve organically. Rejected because mixed styles make a reference set feel fragmented.
- Optimize only for concise contract bullets. Rejected because the docs would remain hard to approach for new readers.

### 6) Turn existing runtime overview pages into link hubs instead of duplicate deep references

`docs/reference/brain_launch_runtime.md` and `docs/reference/agents_brains.md` should continue to exist, but their role should shift:

- explain the broad workflow,
- introduce the existence of the new subtrees,
- link readers into the detailed agent or gateway pages for exact contracts and internals,
- keep only enough embedded detail to remain useful as entrypoints.

`docs/reference/index.md` should also expose both new subtrees directly.

Rationale:

- broader runtime pages still matter for onboarding and discovery,
- keeping detailed contracts in one place avoids divergence,
- this preserves continuity for existing readers while improving depth and structure.

Alternatives considered:

- Remove broad runtime pages entirely. Rejected because the repo still needs high-level entrypoints.
- Keep all existing detail in place and add the new pages on top. Rejected because it would recreate the current duplication problem in a larger surface area.

## Risks / Trade-offs

- [Risk] The new subtrees may still overlap, especially around gateway-aware control commands. → Mitigation: define page ownership up front and cross-link instead of restating protocol details.
- [Risk] The docs could accidentally describe intended extensibility as implemented support. → Mitigation: ground gateway and runtime wording in current source modules and gateway-focused tests.
- [Risk] The reference set could become too page-heavy for casual readers. → Mitigation: keep each `index.md` short and task-oriented, with “read by goal” navigation to the deeper pages.
- [Risk] A friendlier rewrite could lose technical precision. → Mitigation: require exact payload shapes, file-layout details, status axes, and source references after the mental-model section.
- [Risk] Diagrams could become decorative or too wide to read. → Mitigation: add Mermaid sequence diagrams only where the procedure materially helps understanding and keep participant labels concise.
- [Risk] Existing runtime docs may continue to drift if future changes update only one location. → Mitigation: explicitly reposition overview pages as link hubs and make the new detailed pages the main source-aligned reference surfaces.

## Migration Plan

1. Create the new `docs/reference/agents/` and `docs/reference/gateway/` directory structures with index pages plus contracts, operations, and internals subpages.
2. Draft the new pages from the current runtime, gateway, and test surfaces, using concrete examples and diagrams where needed.
3. Update `docs/reference/index.md` and broader runtime reference pages to point to the new subtrees.
4. Trim or rewrite duplicated deep detail in `docs/reference/brain_launch_runtime.md` and `docs/reference/agents_brains.md` so those pages remain overview-oriented.
5. Do a final source-alignment pass against the runtime modules, gateway modules, and gateway-focused tests before implementation is considered complete.

Rollback is straightforward because the change is documentation-only: restore the prior page layout and links if the new split proves confusing or too heavy.

## Open Questions

- Should the first pass include a dedicated quickstart-style page under `docs/reference/agents/`, or should the agent index remain the primary onboarding surface?
- Which procedures most need Mermaid diagrams in the first pass: only lifecycle-heavy pages, or also contract pages where a request path benefits from sequence framing?
- How much mailbox detail should remain in the agent reference pages versus linking out to `docs/reference/mailbox/` when mailbox is one of several runtime message-passing paths?
- Do we want a small shared glossary section duplicated in both subtree indexes, or should each index define only the terms most central to that subsystem?
