## 1. Doc Set Scaffold And Navigation

- [x] 1.1 Create the `docs/developer/tui-parsing/` directory with `index.md` as the landing page and establish the final page filenames and reading order.
- [x] 1.2 Update `docs/index.md` so the new TUI parsing developer docs are discoverable from the main docs entry point.
- [x] 1.3 Update existing shadow-parsing reference and troubleshooting pages to link to the new developer doc set for design-level detail instead of duplicating deep explanations.

## 2. Shared Architecture And Lifecycle Guides

- [x] 2.1 Write `architecture.md` to explain the layered TUI parsing design, including parser ownership, dialog projection, `TurnMonitor`, and optional caller-side answer association.
- [x] 2.2 Write `shared-contracts.md` to document `SurfaceAssessment`, `DialogProjection`, projection slices, parser metadata/anomalies, and the `shadow_only` result surface.
- [x] 2.3 Write `runtime-lifecycle.md` to document `TurnMonitor` states, success terminality, and blocked/stalled/failure behavior, including a Mermaid `stateDiagram-v2` graph.
- [x] 2.4 Add explicit prose or tables in `runtime-lifecycle.md` that define each lifecycle state and explain how the major transition events are detected from parser/runtime observations.

## 3. Provider And Maintenance Guides

- [x] 3.1 Write `claude.md` to capture Claude-specific state vocabulary, UI contexts, detection signals, and projection boundaries.
- [x] 3.2 Write `codex.md` to capture Codex-specific state vocabulary, UI contexts, supported output families, and projection boundaries.
- [x] 3.3 Write `maintenance.md` to explain source-of-truth inputs, drift investigation, coordinated updates across docs/specs/tests, and expectations for future parser-contract revisions.
- [x] 3.4 Add a Mermaid parser-state transition graph plus state or event explanation sections to `claude.md`.
- [x] 3.5 Add a Mermaid parser-state transition graph plus state or event explanation sections to `codex.md`.

## 4. Consistency Review

- [x] 4.1 Re-read the new doc set against `openspec/specs/`, the decouple contract notes, and the active runtime modules to confirm terminology and ownership boundaries are consistent.
- [x] 4.2 Verify Markdown structure, Mermaid blocks, and internal links render cleanly and match repository documentation conventions.
- [x] 4.3 Confirm the final doc set gives developers direct guidance on architecture, state transitions, provider differences, and maintenance without relying on archived change artifacts.
