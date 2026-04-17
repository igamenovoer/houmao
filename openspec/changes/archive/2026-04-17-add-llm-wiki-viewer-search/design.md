## Context

The bundled LLM Wiki viewer is a local Express and TypeScript application under `extern/tracked/llm-wiki-skill/llm-wiki-all-in-one/viewer/web/`. It serves a browser client, exposes JSON APIs for the navigation tree, graph, pages, raw Markdown, audits, and config, and renders Markdown on demand from a user-selected wiki root.

The viewer currently has two discovery paths: the file tree and the knowledge graph. Both are useful for browsing but become slow when a wiki grows beyond the point where users remember article names or folder placement. The search feature should match the feel of MkDocs quick search while respecting the viewer's local-first runtime model.

## Goals / Non-Goals

**Goals:**

- Add quick full-text search across wiki Markdown pages.
- Keep search local to the existing viewer process and browser client.
- Provide responsive as-you-type matching with prefix and typo tolerance.
- Reuse the viewer's existing SPA navigation when a user opens a result.
- Keep implementation small enough to ship with the all-in-one skill and deploy helper.
- Keep indexed content read-only and constrained to valid wiki Markdown pages.

**Non-Goals:**

- Do not add a hosted search service, search daemon, API key, or external network dependency.
- Do not introduce a generated static-site phase or require Pagefind indexes for v1.
- Do not search audit files, generated viewer files, hidden files, attachments, or arbitrary paths outside `wiki/`.
- Do not add semantic/vector search in this change.
- Do not change Markdown rendering, wikilink resolution, graph behavior, or audit write behavior except where search needs navigation integration.

## Decisions

1. Build a read-only search document feed on the server and index it in the browser.

   Add a new route such as `GET /api/search-index` that recursively reads Markdown files under `<wikiRoot>/wiki`, extracts lightweight searchable documents, and returns JSON records with path, title, headings, normalized text, and preview fields. The browser fetches this feed lazily and builds the search index on first search focus or keyboard invocation.

   Alternative considered: implement every query server-side. Server-side search would reduce browser memory use, but it would require request/response traffic on each keystroke and would feel less like MkDocs-style local quick search. It also adds cache invalidation concerns to the server route instead of keeping v1 simple.

2. Use MiniSearch for v1.

   MiniSearch provides browser-capable full-text search with prefix search, fuzzy matching, field boosting, suggestions, and no runtime dependencies. It fits the existing esbuild client bundle and the local wiki size this viewer targets.

   Alternatives considered:

   - Lunr: closest to MkDocs historically, but older and less ergonomic for modern typeahead behavior.
   - Pagefind: strong static-site search, but it expects a generated HTML site and static index bundle; that conflicts with this viewer's dynamic Markdown rendering model.
   - FlexSearch: powerful and fast, but its broader feature surface and configuration complexity are not needed for the initial quick-search feature.
   - Orama: capable, but larger in scope than the local full-text need and oriented toward broader search/RAG scenarios.

3. Search only canonical wiki Markdown content.

   The initial index should include non-hidden `.md` files below `<wikiRoot>/wiki`. It should exclude `audit/`, hidden files/directories, viewer deployment artifacts, and non-Markdown assets. Paths returned to the browser should be canonical vault-root paths already accepted by `/api/page`, such as `wiki/concepts/Transformers.md`.

   Alternative considered: search the entire wiki root. That would index `README.md`, audit feedback, and operational metadata, but it would also mix schema/configuration content into article search and increase leakage of non-reader-facing files.

4. Normalize Markdown into useful search fields rather than rendered HTML.

   The server should extract title from frontmatter or H1, headings from Markdown heading syntax, and searchable text from Markdown source after removing frontmatter and normalizing common wiki syntax. Wikilinks should contribute both alias and target text where practical so searching either `[[Target|Alias]]` term can find the page.

   Alternative considered: render every page to HTML and index DOM text. That would make the index closer to displayed content but couples search indexing to the full renderer, mermaid placeholders, and HTML stripping. Source-based extraction is simpler and easier to test.

5. Add search UI as a small client module.

   Add a topbar search entry point and keyboard shortcut such as `Ctrl+K` or `/`. The result picker should support typing, arrow navigation, Enter to open, Escape to close, and mouse click selection. Opening a result should call the same page-loading flow used by tree and graph navigation and update browser history.

   Alternative considered: filter the existing tree. Tree filtering would help page title discovery but would not search article body text, headings, or wikilink aliases.

## Risks / Trade-offs

- Large wikis could produce a large `/api/search-index` response -> Build the index lazily, cap preview text, avoid returning rendered HTML, and keep v1 scoped to `wiki/**/*.md`.
- Browser indexing can briefly block the UI on very large local wikis -> Keep document records compact and consider server-side cached MiniSearch or Pagefind/qmd later if real wikis exceed the comfortable client-side range.
- Search results may lag behind filesystem edits while the viewer is open -> Fetch the index on first use and provide a refresh/rebuild path, or rebuild when the search dialog is reopened after a debounce/window age threshold if implementation remains simple.
- Markdown normalization may omit specialized syntax -> Treat v1 as title, heading, body text, and wikilink text search; avoid promising rendered-exact search.
- The viewer is unauthenticated and local-only -> Do not expose search on non-local hosts beyond the viewer's existing binding behavior; the new endpoint should be read-only and path-safe.

## Migration Plan

No data migration is required. Existing wiki directories, page URLs, audit files, and deployment metadata remain valid. The deploy helper will copy the updated viewer source and install the new npm dependency during its normal install/build workflow.

Rollback is removing the search UI, route, and dependency; no wiki content or stored viewer data depends on the feature.

## Open Questions

- Should `README.md` be included as a special search result later, or should v1 remain strictly scoped to `wiki/` articles?
- Should the search index refresh automatically when Markdown files change, or is manual viewer refresh sufficient for v1?
