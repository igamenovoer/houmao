## Why

The bundled LLM Wiki web viewer can render and navigate wiki pages, but users must browse the tree or graph to find content. A MkDocs-style quick search would make larger local wikis usable without introducing a hosted service or changing the wiki authoring workflow.

## What Changes

- Add a local quick-search capability to the bundled LLM Wiki viewer.
- Index Markdown pages under the wiki's `wiki/` directory and expose searchable document metadata to the browser.
- Provide a topbar search entry point and keyboard-driven result picker that opens selected pages through the existing SPA navigation path.
- Use a lightweight third-party JavaScript search library suitable for client-side prefix/fuzzy full-text search.
- Keep the viewer local-first and self-contained: no external search service, API key, daemon, or generated static-site phase.

## Capabilities

### New Capabilities

- `llm-wiki-viewer-search`: Defines local full-text quick search for the bundled LLM Wiki web viewer, including indexed content scope, client search behavior, result navigation, and dependency expectations.

### Modified Capabilities

## Impact

- Affected code: `extern/tracked/llm-wiki-skill/llm-wiki-all-in-one/viewer/web/`
- Affected docs: `extern/tracked/llm-wiki-skill/README.md`, `extern/tracked/llm-wiki-skill/llm-wiki-all-in-one/SKILL.md`, and viewer deployment/reference notes as needed
- New dependency: a lightweight browser-capable JavaScript full-text search library, expected to be `minisearch`
- Affected behavior: the viewer exposes a read-only search index endpoint and adds a search UI to the browser client
