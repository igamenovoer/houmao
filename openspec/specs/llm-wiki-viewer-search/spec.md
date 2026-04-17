# llm-wiki-viewer-search Specification

## Purpose
TBD - created by archiving change add-llm-wiki-viewer-search. Update Purpose after archive.
## Requirements
### Requirement: Viewer Exposes Searchable Wiki Documents
The LLM Wiki viewer SHALL expose a read-only search document feed for Markdown pages under the active wiki root's `wiki/` directory.

#### Scenario: Search feed indexes wiki Markdown pages
- **WHEN** the viewer is serving a wiki root that contains non-hidden Markdown files under `wiki/`
- **THEN** the search feed includes one document per indexed Markdown file with a canonical page path, title, headings, searchable text, and preview text

#### Scenario: Search feed excludes non-article content
- **WHEN** the wiki root contains audit files, hidden files, generated viewer files, non-Markdown files, or files outside `wiki/`
- **THEN** the search feed excludes those files

#### Scenario: Search feed keeps paths inside wiki root
- **WHEN** the search feed resolves files for indexing
- **THEN** every returned document path is relative to the wiki root and cannot escape the wiki root

### Requirement: Viewer Provides Client-Side Quick Search
The LLM Wiki viewer SHALL provide a browser quick-search UI backed by a lightweight client-side full-text index.

#### Scenario: User opens quick search
- **WHEN** the user activates the search control or supported keyboard shortcut
- **THEN** the viewer focuses a search input without navigating away from the current page

#### Scenario: User types a query
- **WHEN** the user types a non-empty query into the search input
- **THEN** the viewer returns ranked matching wiki pages using title, headings, body text, and page path fields

#### Scenario: Search supports quick partial matching
- **WHEN** the user enters a partial word or a query containing a minor typo
- **THEN** the viewer can return relevant matches using prefix and fuzzy matching

#### Scenario: Empty search is stable
- **WHEN** the search input is empty
- **THEN** the viewer does not display stale results from a previous query

### Requirement: Search Results Navigate Through Existing Page Loading
Search results SHALL open pages through the viewer's existing single-page navigation behavior.

#### Scenario: User selects a search result
- **WHEN** the user selects a search result by keyboard or pointer
- **THEN** the viewer loads the selected page through the same page-loading path used by tree and graph navigation
- **AND** browser history reflects the selected page URL

#### Scenario: Search result points to current page
- **WHEN** the user selects a search result for the currently loaded page
- **THEN** the viewer keeps the page in a valid loaded state and closes or clears the search UI

### Requirement: Search Runs Without External Services
The LLM Wiki viewer search SHALL run without a hosted search service, external API key, separate daemon, or generated static-site search phase.

#### Scenario: Viewer is deployed locally
- **WHEN** the viewer is installed and launched by the existing deploy helper
- **THEN** search works from the viewer process and bundled browser assets after dependency installation and client build

#### Scenario: Search dependency is installed
- **WHEN** the viewer package dependencies are installed
- **THEN** the selected third-party search library is resolved from the viewer package manager workflow and bundled with the client assets as needed

### Requirement: Search UI Handles Keyboard Operation
The LLM Wiki viewer search SHALL support keyboard-oriented operation appropriate for quick navigation.

#### Scenario: User navigates results by keyboard
- **WHEN** search results are visible and the user presses arrow keys
- **THEN** the active result selection changes without leaving the search input

#### Scenario: User confirms a selected result
- **WHEN** a search result is active and the user presses Enter
- **THEN** the viewer opens that result

#### Scenario: User dismisses search
- **WHEN** the search UI is open and the user presses Escape
- **THEN** the viewer dismisses search without changing the currently loaded page
