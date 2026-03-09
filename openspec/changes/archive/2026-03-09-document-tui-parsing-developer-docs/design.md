## Context

`decouple-shadow-state-from-answer-association` established the repository's current TUI parsing architecture: provider parsers classify single snapshots into `SurfaceAssessment` and `DialogProjection`, `TurnMonitor` owns submit-aware lifecycle across snapshots, and caller-side answer association is intentionally optional and separate. That design is now captured in change-local materials such as `openspec/changes/decouple-shadow-state-from-answer-association/design.md` and the Claude, Codex, and `TurnMonitor` contract notes, while the main docs tree only has a concise reference page and a troubleshooting page.

This leaves a gap for developers who need to understand or extend the parser stack. The official docs do not yet provide a durable, discoverable explanation of the design boundaries, the runtime state machine, or the provider-specific contracts. Because the contract has now stabilized enough to archive the originating change, we need to publish a maintained documentation set in `docs/` before that context is harder to discover.

## Goals / Non-Goals

**Goals:**
- Publish an official developer-oriented TUI parsing documentation set under `docs/developer/tui-parsing/`.
- Split the material into focused pages so architecture, shared contracts, runtime lifecycle, provider-specific rules, and maintenance guidance can evolve without one monolithic document.
- Give developers a clear reading path from docs navigation into the new deep-dive pages.
- Preserve a clear boundary between developer deep dives and operator/reference/troubleshooting pages.
- Document the current source-of-truth mapping between docs, contract notes, OpenSpec specs, and runtime modules so future updates are easier to maintain.

**Non-Goals:**
- Change runtime behavior, parser semantics, or OpenSpec capability requirements beyond documentation coverage.
- Replace the existing troubleshooting guide with a full architecture manual.
- Freeze every regex or implementation detail in public docs; the documentation should describe stable concepts and named predicates rather than become a line-for-line code mirror.
- Create a general-purpose `docs/developer/` information architecture beyond what this TUI parsing doc set needs right now.

## Decisions

### 1. Create an aspect-oriented documentation set instead of a single long page

The implementation target will be a dedicated directory:

- `docs/developer/tui-parsing/index.md`
- `docs/developer/tui-parsing/architecture.md`
- `docs/developer/tui-parsing/shared-contracts.md`
- `docs/developer/tui-parsing/runtime-lifecycle.md`
- `docs/developer/tui-parsing/claude.md`
- `docs/developer/tui-parsing/codex.md`
- `docs/developer/tui-parsing/maintenance.md`

`index.md` will explain the purpose of the doc set, define the recommended reading order, and link to the deeper pages.

Rationale:
- The user explicitly asked for docs focused on different aspects.
- Architecture, shared contracts, runtime lifecycle, and provider-specific rules change at different cadences and benefit from separate pages.
- Separate provider pages let Claude and Codex evolve independently without forcing every edit through one merged provider appendix.

Alternatives considered:
- One monolithic `tui-parsing.md` page.
Why not:
- It would be harder to scan, harder to maintain, and more likely to mix stable concepts with provider-specific details.

### 2. Keep reference docs concise and move deep design material into developer docs

The repository already has `docs/reference/cao_claude_shadow_parsing.md` and `docs/reference/cao_shadow_parser_troubleshooting.md`. We will keep those pages as concise reference and operational entry points, then link to the new developer doc set for deeper architecture and contract explanation.

`docs/index.md` will gain a developer-oriented entry that points at `docs/developer/tui-parsing/index.md` so the new material is not hidden behind direct URLs.

Rationale:
- Reference pages and troubleshooting guides serve a different audience than architecture docs.
- Leaving long-form design details duplicated in multiple places would guarantee drift.

Alternatives considered:
- Expand the existing reference page until it becomes the developer guide.
Why not:
- It would blur operator/reference content with contributor-facing design documentation and duplicate troubleshooting material.

### 3. Use the decouple change artifacts as normative inputs, but not as the published doc format

The new docs will be derived from these current sources of truth:

- `openspec/changes/decouple-shadow-state-from-answer-association/design.md`
- `openspec/changes/decouple-shadow-state-from-answer-association/contracts/claude-state-contracts.md`
- `openspec/changes/decouple-shadow-state-from-answer-association/contracts/codex-state-contracts.md`
- `openspec/changes/decouple-shadow-state-from-answer-association/contracts/turn-monitor-contracts.md`
- the active capability specs in `openspec/specs/`
- the runtime implementation under `src/gig_agents/agents/brain_launch_runtime/backends/`

The developer docs will summarize and structure that material into a maintained repository guide. They should reference the underlying code/spec inputs where useful, but they should not copy raw change-local notes verbatim.

Rationale:
- Change-local contract notes are useful for design history, but they are not a good long-term public navigation surface.
- A curated doc set lets us normalize terminology and cross-links for future developers.

Alternatives considered:
- Publish the contract notes directly under `docs/` with minimal editing.
Why not:
- The notes are optimized for change discussion, not long-term documentation flow, and they repeat background that should instead live in a cleaner reading path.

### 4. Represent architecture, runtime lifecycle, and provider parser states with Mermaid diagrams

The new docs will use Mermaid blocks for the core data flow and `TurnMonitor` lifecycle/state-transition material.

At minimum:
- `architecture.md` should show the layered path from CAO/tmux snapshot to parser artifacts to runtime lifecycle and optional answer association.
- `runtime-lifecycle.md` should include a Mermaid `stateDiagram-v2` graph for `TurnMonitor`.
- `runtime-lifecycle.md` should define each runtime lifecycle state in prose.
- `runtime-lifecycle.md` should define the transition events in prose or tabular form, including how they are detected from parser observations.
- `claude.md` should include a Mermaid `stateDiagram-v2` graph for Claude parser-state transitions and explain Claude-specific state meanings and transition events.
- `codex.md` should include a Mermaid `stateDiagram-v2` graph for Codex parser-state transitions and explain Codex-specific state meanings and transition events.

Rationale:
- The repository guidance prefers Mermaid for UML-style diagrams in Markdown.
- The state machine is one of the hardest parts to keep in working memory; a rendered diagram makes the contract easier to review.
- The graph alone is not enough; maintainers also need precise state and event definitions so they can reason about runtime behavior without reverse-engineering code paths.
- The runtime lifecycle graph and the provider parser-state graphs answer different questions, so both are needed: runtime explains turn progression, while provider pages explain one-snapshot parser-state transitions.

Alternatives considered:
- ASCII diagrams or prose-only descriptions.
Why not:
- They are harder to maintain, harder to scan, and less consistent with repository guidance.

### 5. Include an explicit maintenance page so future parser changes update docs deliberately

The doc set will include a `maintenance.md` page that explains:
- the source-of-truth inputs for the doc set,
- how provider drift should be investigated,
- which fixtures/tests/specs/docs should be updated together, and
- how reference pages should link to the deeper developer material.

Rationale:
- TUI parsing contracts are sensitive to provider drift and can easily become tribal knowledge.
- A maintenance page reduces the chance that future parser work updates tests and code but leaves the official docs stale.

Alternatives considered:
- Leave maintenance expectations implicit in the contributor's head.
Why not:
- The repo has already accumulated contract knowledge in scattered change notes; explicit maintenance guidance is the whole point of this change.

## Risks / Trade-offs

- [The docs may drift from the implementation or OpenSpec contracts] -> Mitigation: document the source-of-truth inputs, keep provider/runtime pages mapped to specific code and spec areas, and add a maintenance page that describes coordinated updates.
- [The doc set may feel fragmented across too many pages] -> Mitigation: use `index.md` as the landing page with a recommended reading order and clear one-sentence descriptions for each page.
- [Reference pages may still duplicate deep design details] -> Mitigation: explicitly scope the reference pages as short entry points and point them to the developer docs for architecture and contract detail.
- [Provider-specific pages may diverge in style or depth] -> Mitigation: use a parallel page structure for Claude and Codex so both pages answer the same categories of questions.

## Migration Plan

1. Create `docs/developer/tui-parsing/` with the planned landing page and aspect-focused documents.
2. Populate the pages from the decouple design/contracts, active specs, and runtime modules while normalizing terminology for long-term maintenance.
3. Update `docs/index.md` and existing shadow-parsing reference/troubleshooting pages to link into the new developer docs.
4. Re-read the final doc set against the active runtime/spec contract to confirm that architecture, state transitions, and provider boundaries are described consistently.

Rollback strategy:
- If the new structure proves confusing, we can remove the new links and pages without affecting runtime behavior. Because this change is documentation-only, rollback is a content/navigation revert rather than a runtime migration.

## Open Questions

- None at proposal time; the document set shape is clear enough to proceed without additional discovery.
