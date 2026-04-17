## 1. Remove Graph Server Surface

- [x] 1.1 Remove `/api/graph` route registration from the viewer server.
- [x] 1.2 Delete the server graph route module.

## 2. Remove Graph Client Surface

- [x] 2.1 Remove graph imports, state, handlers, and keyboard shortcut logic from the viewer client entrypoint.
- [x] 2.2 Remove the Graph button and graph overlay markup from the client HTML.
- [x] 2.3 Delete graph-only client modules.
- [x] 2.4 Remove graph-only CSS variables and graph overlay styles.

## 3. Remove Dependencies And Docs

- [x] 3.1 Remove graph-only D3 dependencies and type packages from the viewer package manifest.
- [x] 3.2 Update viewer-facing documentation to stop advertising the bundled web viewer graph.
- [x] 3.3 Keep Obsidian graph documentation and non-viewer graph/link semantics intact.

## 4. Verification

- [x] 4.1 Search the viewer source for stale web viewer graph references.
- [x] 4.2 Run the viewer route tests.
- [x] 4.3 Run the viewer TypeScript typecheck.
- [x] 4.4 Run the viewer client build.
- [x] 4.5 Run `openspec status --change remove-llm-wiki-viewer-graph` and confirm the change is apply-ready.
