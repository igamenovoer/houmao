## Context

The bundled LLM Wiki web viewer currently includes a force-directed graph implementation: a server-side `/api/graph` route builds graph nodes and edges from wikilinks, and the browser client renders those nodes with D3 plus a canvas particle background. The viewer now also has navigation tree and quick search, so the graph is no longer needed in this web surface.

## Goals / Non-Goals

**Goals:**

- Remove the web viewer graph UI and API.
- Remove graph-only client modules and server route code.
- Remove graph-only npm dependencies and type packages.
- Keep reading, navigation tree, search, wikilinks, Mermaid, KaTeX, and audit feedback behavior intact.
- Keep Obsidian graph guidance intact where it refers to Obsidian rather than the bundled web viewer.

**Non-Goals:**

- Do not alter wiki link semantics, lint/orphan checking, or Obsidian workflows.
- Do not change search indexing or navigation tree behavior.
- Do not add a replacement visualization.
- Do not add compatibility shims for `/api/graph`.

## Decisions

1. Remove the web viewer graph feature completely.

   Delete the Graph button, overlay markup, graph keyboard shortcut, graph client imports, D3 graph renderer, particle background module, `/api/graph` route registration, and server graph builder. This avoids leaving dead code or a hidden endpoint for a feature the viewer no longer needs.

   Alternative considered: hide the Graph button but keep `/api/graph` and graph modules. That would reduce visible UI but preserve unused complexity, dependencies, and build weight.

2. Remove graph dependencies from the viewer package.

   The graph renderer is the only consumer of `d3-drag`, `d3-force`, `d3-selection`, `d3-zoom`, and their type packages. Removing those dependencies makes installs smaller and prevents the client bundle from carrying graph-only code.

   Alternative considered: keep D3 dependencies for future use. This conflicts with the goal of simplifying the bundled viewer now.

3. Keep Obsidian graph docs and non-viewer link semantics.

   Existing guidance about Obsidian's graph view and wiki graph/orphan checks belongs to the broader LLM Wiki workflow. This change removes only the bundled web viewer graph.

   Alternative considered: remove every mention of graph in the repo. That would overreach and accidentally strip useful Obsidian and linting concepts.

## Risks / Trade-offs

- Users relying on the web viewer Graph button lose that visualization -> Mitigate by preserving search and navigation tree and by keeping Obsidian graph guidance for users who want graph exploration.
- Documentation may leave stale web viewer graph references -> Mitigate with targeted searches for `Graph`, `graph-overlay`, `/api/graph`, and D3 dependencies after implementation.
- Removing dependencies can reveal accidental imports -> Mitigate by running the viewer typecheck and client build.

## Migration Plan

No data migration is required. Existing wiki content, links, audit files, search behavior, and page URLs remain valid. Deploying the updated viewer removes the graph UI/API from future installs.

Rollback is restoring the removed graph modules, route, UI markup, CSS, and dependencies.
