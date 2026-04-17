## 1. Search Dependency And API

- [x] 1.1 Add `minisearch` to the viewer package dependencies and refresh the viewer lockfile through the package manager workflow.
- [x] 1.2 Add a server search route module that collects non-hidden `.md` files under `<wikiRoot>/wiki`.
- [x] 1.3 Implement path safety checks so indexed files and returned paths remain inside the wiki root.
- [x] 1.4 Extract search document fields from Markdown source: canonical path, title, headings, searchable text, and preview text.
- [x] 1.5 Normalize frontmatter, Markdown headings, links, and wikilinks so common article terms and aliases are searchable.
- [x] 1.6 Mount the read-only search feed route from the viewer server.

## 2. Client Search UI

- [x] 2.1 Add a client search module that lazily fetches the search document feed and builds a MiniSearch index.
- [x] 2.2 Configure MiniSearch fields, stored fields, prefix matching, fuzzy matching, and field boosts for title, headings, body text, and path.
- [x] 2.3 Add topbar search markup and styles that fit the existing viewer layout.
- [x] 2.4 Implement keyboard shortcuts to open search and focus the input without disrupting editable controls.
- [x] 2.5 Render stable search result rows with title, path, and preview text.
- [x] 2.6 Clear stale result display when the query is empty or the search UI is dismissed.

## 3. Navigation Integration

- [x] 3.1 Wire pointer selection to load the selected page through the existing SPA page-loading flow.
- [x] 3.2 Wire keyboard result navigation with arrow keys, Enter to open, and Escape to dismiss.
- [x] 3.3 Update browser history when a result opens, matching tree and graph navigation behavior.
- [x] 3.4 Handle selecting the currently loaded page without leaving the viewer in a stale search state.

## 4. Documentation

- [x] 4.1 Update viewer/user-facing documentation to mention local quick search and its keyboard shortcut.
- [x] 4.2 Update deploy or tooling notes if the added dependency changes install, build, or troubleshooting expectations.

## 5. Verification

- [x] 5.1 Add or update tests for search document extraction, including frontmatter title, H1 fallback, headings, body text, wikilinks, and preview generation.
- [x] 5.2 Add or update tests for search indexing scope, including exclusion of hidden files, non-Markdown files, audit files, and paths outside `wiki/`.
- [x] 5.3 Run the viewer TypeScript build or typecheck command available in the package.
- [x] 5.4 Run the viewer client build to confirm MiniSearch bundles correctly.
- [x] 5.5 Manually verify search in the local viewer with title, heading, body phrase, partial word, typo, and wikilink alias queries.
- [x] 5.6 Run `openspec status --change add-llm-wiki-viewer-search` and confirm the change is apply-ready.
