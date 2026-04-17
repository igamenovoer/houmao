## Why

The bundled LLM Wiki web viewer currently includes a force-directed entity/knowledge graph, but the viewer no longer needs that surface. Removing it simplifies the UI, reduces bundled JavaScript and dependencies, and keeps the web viewer focused on reading, search, navigation, and audit feedback.

## What Changes

- Remove the web viewer's Graph button, graph overlay, graph keyboard shortcut, and graph client modules.
- Remove the read-only `/api/graph` route and server-side graph builder from the bundled viewer.
- Remove D3 graph dependencies and matching type packages from the viewer package.
- Update viewer-facing docs so they no longer advertise the bundled web viewer graph.
- Preserve Obsidian graph-view guidance and unrelated wiki link/lint semantics unless they specifically refer to the web viewer graph.

## Capabilities

### New Capabilities

- `llm-wiki-viewer-no-graph`: Defines that the bundled LLM Wiki web viewer omits the graph surface and graph API while retaining reading, search, navigation tree, Mermaid rendering, math rendering, wikilinks, and audit feedback.

### Modified Capabilities

## Impact

- Affected code: `extern/tracked/llm-wiki-skill/llm-wiki-all-in-one/viewer/web/`
- Affected docs: viewer/user-facing documentation under `extern/tracked/llm-wiki-skill/`
- Removed dependencies: `d3-drag`, `d3-force`, `d3-selection`, `d3-zoom`, and corresponding `@types/d3-*` packages
- Removed API: `GET /api/graph`
