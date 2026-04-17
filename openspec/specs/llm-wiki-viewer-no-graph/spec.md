# llm-wiki-viewer-no-graph Specification

## Purpose
TBD - created by archiving change remove-llm-wiki-viewer-graph. Update Purpose after archive.
## Requirements
### Requirement: Web Viewer Omits Graph UI
The bundled LLM Wiki web viewer SHALL NOT expose a graph button, graph overlay, or graph-specific keyboard shortcut.

#### Scenario: Viewer topbar renders
- **WHEN** the bundled web viewer client renders its topbar
- **THEN** no Graph control is shown

#### Scenario: Viewer keyboard shortcuts run
- **WHEN** the bundled web viewer receives keyboard input
- **THEN** it does not open a graph overlay or reserve a graph-specific shortcut

### Requirement: Web Viewer Omits Graph API
The bundled LLM Wiki web viewer SHALL NOT expose a graph API endpoint.

#### Scenario: Viewer server routes are registered
- **WHEN** the bundled web viewer server starts
- **THEN** it does not register `GET /api/graph`

### Requirement: Web Viewer Excludes Graph Dependencies
The bundled LLM Wiki web viewer package SHALL NOT depend on graph-only D3 packages.

#### Scenario: Viewer dependencies are installed
- **WHEN** the bundled web viewer package dependencies are resolved
- **THEN** graph-only D3 packages and matching graph-only D3 type packages are not required by the package manifest

### Requirement: Non-Graph Viewer Features Remain Available
Removing the web viewer graph SHALL preserve the viewer's remaining reading and feedback workflows.

#### Scenario: Viewer client builds without graph modules
- **WHEN** the bundled web viewer client is built
- **THEN** reading, navigation tree, quick search, wikilinks, Mermaid rendering, KaTeX rendering, and audit feedback code remain buildable
