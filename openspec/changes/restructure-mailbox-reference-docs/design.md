## Context

The mailbox feature now spans several different surfaces:

- runtime session integration and env binding resolution in `src/gig_agents/agents/mailbox_runtime_support.py`,
- runtime-owned mailbox prompt and result handling in `src/gig_agents/agents/brain_launch_runtime/mail_commands.py`,
- canonical protocol and message validation in `src/gig_agents/mailbox/protocol.py`,
- filesystem bootstrap, registration lookup, and SQLite layout in `src/gig_agents/mailbox/filesystem.py`,
- managed helper validation and mutation boundaries in `src/gig_agents/mailbox/managed.py`,
- mailbox-local projected rules and protocol notes under `src/gig_agents/mailbox/assets/rules/`,
- projected system-skill guidance under `src/gig_agents/agents/brain_launch_runtime/assets/system_skills/mailbox/`.

Today the main repo docs compress most of that into `docs/reference/mailbox.md`, with a few mailbox notes also living in `docs/reference/brain_launch_runtime.md`. That makes the mailbox docs broad but shallow: readers get a useful overview, but detailed contracts, operational rules, and internals are mixed together instead of being easy to navigate.

The documentation problem is not lack of content so much as lack of structure. The implementation already contains strong source material, but the repo-level reference does not yet present it as a coherent documentation system.

## Goals / Non-Goals

**Goals:**

- Create a stable mailbox documentation information architecture under `docs/reference/mailbox/`.
- Separate high-level orientation from detailed contracts, operations, and internals so different readers can find the right depth quickly.
- Make each mailbox reference page understandable to a new reader before requiring mailbox-specific context.
- Make the mailbox reference pages explicitly traceable to the relevant code and projected mailbox assets.
- Reduce duplicated mailbox detail in broader runtime docs by pointing readers into the mailbox reference subtree.
- Keep the new documentation shape compatible with future mailbox work, including additional transports or deeper lifecycle features.
- Preserve technical precision so developers can still use the docs as an exact implementation-facing reference.

**Non-Goals:**

- No runtime behavior change, transport change, SQLite schema change, or managed-helper contract change.
- No attempt to document every implementation function line-by-line.
- No requirement to expose projected mailbox-local assets verbatim inside repo docs.
- No reorganization of unrelated non-mailbox reference docs beyond link updates needed to reach the new mailbox subtree.

## Decisions

### 1) Replace the single mailbox page with a mailbox reference subtree

The mailbox reference surface will move from one file at `docs/reference/mailbox.md` to a directory rooted at `docs/reference/mailbox/`, with `index.md` as the navigational entrypoint.

The subtree should be organized by reader intent rather than by the Python module layout. The recommended first-pass structure is:

- `docs/reference/mailbox/index.md`
- `docs/reference/mailbox/quickstart.md`
- `docs/reference/mailbox/contracts/`
- `docs/reference/mailbox/operations/`
- `docs/reference/mailbox/internals/`

Rationale:

- readers often start with a task or question, not a source file name,
- the mailbox system now has enough depth that contracts and internals should not compete for space on the same page,
- a subtree gives room to grow without turning one page into a catch-all index.

Alternatives considered:

- Keep `docs/reference/mailbox.md` and expand it further. Rejected because the current page is already mixing too many audiences and concerns.
- Mirror the Python package layout directly in the docs tree. Rejected because it optimizes for source familiarity rather than reference usability.

### 2) Organize mailbox docs around three layers: contracts, operations, internals

The detailed mailbox reference should separate:

- **contracts**: stable surfaces readers must follow,
- **operations**: safe workflows and lifecycle guidance,
- **internals**: implementation model and architecture.

Recommended page responsibilities:

- `contracts/`
  - canonical message model
  - runtime mailbox bindings and `mail` command contract
  - managed helper script contract
  - filesystem layout contract
- `operations/`
  - common mailbox workflows
  - registration lifecycle
  - repair and recovery
- `internals/`
  - end-to-end architecture
  - SQLite, locking, and mutable-state model

Rationale:

- the mailbox feature already has stable operator-facing contracts that deserve explicit documentation,
- lifecycle guidance and internal design notes are both important, but they answer different questions,
- this split gives a durable place for future mailbox changes to land without duplicating material awkwardly.

Alternatives considered:

- Organize only by user role such as operator vs developer. Rejected because the same reader may need contract details plus internals in the same session.
- Organize only by lifecycle stage such as bootstrap/send/repair. Rejected because it hides the enduring contracts that apply across all stages.

### 3) Use a layered writing pattern inside each detailed mailbox page

Each detailed mailbox reference page should follow a consistent shape that starts with intuitive understanding and then moves into exact detail.

The recommended writing pattern is:

1. short page-purpose statement that tells the reader what question this page answers,
2. a mental model or plain-language overview,
3. the exact technical details, constraints, or contracts,
4. one or more concrete examples or walkthrough fragments,
5. an embedded Mermaid diagram when the page introduces an important procedure or interaction flow,
6. source references pointing to the implementation files or projected mailbox assets reflected by that page.

Important mailbox terms should be introduced before being used heavily. Pages should not assume that the reader already understands concepts such as canonical messages, mailbox registrations, projections, or binding refresh.

Rationale:

- new readers need orientation before dense contract material,
- developers still need exactness and concrete examples, not simplified prose alone,
- a consistent page rhythm makes the mailbox subtree easier to scan and maintain.

Alternatives considered:

- Allow each page to choose its own style. Rejected because the mailbox docs are already fragmented enough without inconsistent presentation.
- Optimize pages only for experienced maintainers. Rejected because the user need here is explicitly broader: first-time readers and developers should both be able to use the docs effectively.

### 4) Use embedded Mermaid sequence diagrams for important procedures

When a mailbox reference page introduces an important procedure, the page should include an embedded Mermaid `sequenceDiagram` block directly in the Markdown file instead of relying on prose alone.

This requirement applies especially to procedural topics such as:

- runtime mailbox bootstrap or enablement flow,
- runtime `mail check`, `mail send`, and `mail reply` flow,
- mailbox registration and deregistration lifecycle flow,
- repair or recovery sequences where multiple components interact.

The diagrams should stay readable in common Markdown renderers by using short participant identifiers, concise message labels, and wrapped labels where needed instead of very wide one-line diagrams.

Rationale:

- important mailbox procedures cross several components and are easier to understand visually,
- a sequence diagram makes the flow easier for new readers to follow without weakening the prose reference,
- embedding the diagram in the page keeps the explanation and the flow in the same place.

Alternatives considered:

- Use prose examples only. Rejected because some mailbox procedures are interaction-heavy and benefit strongly from visual sequencing.
- Use external images or separate diagram files. Rejected because inline Mermaid in the Markdown page keeps the docs easier to maintain and review.

### 5) Treat implementation files and projected mailbox assets as documentation inputs, not parallel reference sites

The repo docs should synthesize and explain the mailbox system, while the projected mailbox-local assets and system-skill references remain concise operational material for the runtime itself.

Each detailed mailbox reference page should identify the source files or asset documents it reflects. In particular, the mailbox reference should stay aligned with:

- `src/gig_agents/mailbox/protocol.py`
- `src/gig_agents/mailbox/filesystem.py`
- `src/gig_agents/mailbox/managed.py`
- `src/gig_agents/mailbox/assets/rules/README.md`
- `src/gig_agents/mailbox/assets/rules/protocols/filesystem-mailbox-v1.md`
- `src/gig_agents/agents/mailbox_runtime_support.py`
- `src/gig_agents/agents/brain_launch_runtime/mail_commands.py`
- `src/gig_agents/agents/brain_launch_runtime/assets/system_skills/mailbox/email-via-filesystem/`

Rationale:

- the repo docs should be more explanatory than the projected assets,
- the projected assets should stay operational and mailbox-local rather than becoming the primary long-form reference,
- explicit source mapping reduces drift when mailbox behavior evolves.

Alternatives considered:

- Duplicate the projected asset text directly into repo docs. Rejected because it increases drift and blurs ownership.
- Treat the projected assets as the only mailbox documentation. Rejected because they are runtime material, not curated reference docs for repo readers.

### 6) Keep broader runtime docs as entry points, not secondary mailbox manuals

`docs/reference/brain_launch_runtime.md` should continue to explain mailbox enablement and the existence of `mail check/send/reply`, but detailed mailbox behavior should live in the dedicated mailbox subtree.

Top-level docs navigation should point to the mailbox subtree from:

- `docs/index.md`
- `docs/reference/index.md`
- `docs/reference/brain_launch_runtime.md`

Rationale:

- runtime docs still need enough mailbox context to make session-control workflows understandable,
- duplicating the full mailbox reference in runtime docs would recreate the current sprawl in a second location,
- keeping runtime docs concise makes the mailbox subtree the obvious home for detail.

Alternatives considered:

- Move all mailbox discussion out of runtime docs entirely. Rejected because mailbox enablement is part of the runtime experience.

## Risks / Trade-offs

- [Risk] The new mailbox subtree could drift from projected mailbox assets and source code. → Mitigation: explicitly anchor each page to specific source files or mailbox asset docs and update those references during mailbox changes.
- [Risk] Too many mailbox pages could make simple onboarding feel heavier than today. → Mitigation: keep `index.md` and `quickstart.md` short and task-oriented, with deeper detail pushed into subpages.
- [Risk] The docs may accidentally describe planned mailbox features as if they already exist. → Mitigation: keep each page explicit about v1 scope and clearly distinguish implemented behavior from future-email compatibility notes.
- [Risk] `brain_launch_runtime.md` and mailbox docs could still duplicate each other. → Mitigation: define `brain_launch_runtime.md` as the enablement-and-linking surface and move detailed contracts into `docs/reference/mailbox/`.
- [Risk] A “friendly” rewrite could oversimplify mailbox behavior and weaken the docs as a technical reference. → Mitigation: require each page to include exact constraints, examples, and source references after the intuitive overview.
- [Risk] A very detailed rewrite could still overwhelm new readers. → Mitigation: use page-purpose statements, mental models, and explicit terminology introduction before dense technical sections.
- [Risk] Added diagrams could become noisy or too wide to read comfortably. → Mitigation: require Mermaid sequence diagrams only for important procedures and keep them renderer-friendly with short participant IDs and concise wrapped labels.

## Migration Plan

1. Create `docs/reference/mailbox/` and replace the current one-file mailbox page with `index.md`.
2. Add the detailed mailbox subpages for contracts, operations, and internals.
3. Update docs navigation and runtime reference links to target the new subtree.
4. Trim mailbox detail from `docs/reference/brain_launch_runtime.md` where it now duplicates the dedicated mailbox pages.
5. Verify the resulting mailbox docs remain consistent with the code and projected mailbox assets they cite.

Rollback is straightforward: restore the prior one-file mailbox reference layout and remove the mailbox subtree links if the reorganization proves confusing.

## Open Questions

- Should the first pass include a dedicated page for the SQLite schema and lock ordering, or should that stay combined in one internals page until the mailbox implementation grows further?
- Do we want a separate “operator troubleshooting” page in the first pass, or is that better deferred until we see repeated failure modes in real usage?
- Should the mailbox index include a small glossary of recurring terms such as canonical message, projection, registration, and binding refresh, or should each page define those terms independently on first use?
- Which procedure pages in the first pass most need diagrams: only operations pages, or also the runtime-integration internals page when it explains multi-component flows?
