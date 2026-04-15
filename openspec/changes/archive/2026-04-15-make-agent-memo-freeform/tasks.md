## 1. Core Memory Helpers

- [x] 1.1 Remove generated memo page-index constants and helper functions from the managed memory helper module.
- [x] 1.2 Stop page write, append, and delete helpers from mutating `houmao-memo.md`.
- [x] 1.3 Add a contained page path-resolution helper that returns page-relative path, memo-relative link, absolute path, existence, and kind metadata.
- [x] 1.4 Keep memo read, replace, and append helpers explicit and free of generated-section handling.

## 2. Boundary Models And Gateway Runtime

- [x] 2.1 Remove gateway memory reindex request/action models and `reindex_memo` action values.
- [x] 2.2 Add gateway memory page path-resolution request/response models.
- [x] 2.3 Update live gateway memory service methods and routes to expose page path resolution.
- [x] 2.4 Remove live gateway `/v1/memory/reindex` behavior.
- [x] 2.5 Include path-discovery metadata in page tree/read/write/delete responses where useful.

## 3. Pair, Passive, And CLI Surfaces

- [x] 3.1 Update pair-server client, service, and app memory proxy routes to remove reindex and proxy page path resolution.
- [x] 3.2 Update passive-server proxy routes and service methods to remove reindex and proxy page path resolution.
- [x] 3.3 Remove `houmao-mgr agents memory reindex`.
- [x] 3.4 Add or update `houmao-mgr agents memory resolve --path <page>` to print page-relative path, memo-relative link, absolute path, existence, and kind.
- [x] 3.5 Update local and server-backed CLI memory command paths to share the same response schema.

## 4. Documentation And Skills

- [x] 4.1 Update the managed memory getting-started guide to describe `houmao-memo.md` as free-form Markdown with authored page links.
- [x] 4.2 Update system-files, README, CLI reference, and mailbox boundary docs to remove generated index and reindex wording.
- [x] 4.3 Update pairwise-v2 initialization guidance to use explicit memo links or path-discovery output for supporting pages.
- [x] 4.4 Search packaged system skills and docs for stale generated-index, reindex, and automatic page-link language.

## 5. Tests And Validation

- [x] 5.1 Update memory helper tests so page mutations leave memo content unchanged.
- [x] 5.2 Add tests for contained page path-resolution metadata and traversal rejection.
- [x] 5.3 Update gateway, pair-proxy, passive-proxy, and CLI tests for resolve behavior and removed reindex behavior.
- [x] 5.4 Update docs/system-skill tests for free-form memo language.
- [x] 5.5 Run `pixi run lint`, `pixi run typecheck`, targeted memory/gateway/CLI tests, and `pixi run test`.
- [x] 5.6 Run `openspec status --change make-agent-memo-freeform` and `openspec validate make-agent-memo-freeform --strict`.
