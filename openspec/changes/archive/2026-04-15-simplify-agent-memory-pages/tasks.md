## 1. Core Memory Model

- [x] 1.1 Replace the scratch/persist workspace helper model with a memo-pages memory model that resolves `memory_root`, `memo_file`, and `pages_dir`.
- [x] 1.2 Implement memory root creation that preserves existing `houmao-memo.md`, creates `pages/`, and does not create `scratch/` or `persist/`.
- [x] 1.3 Implement contained page path resolution with rejection for empty paths, absolute paths, parent traversal, symlink escapes, and NUL-containing content.
- [x] 1.4 Implement memo page-index rendering, supported page mutation index refresh, and explicit reindex behavior that preserves memo content outside managed markers.
- [x] 1.5 Rename exported memory env constants and env generation to `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`.

## 2. Runtime And Manifest

- [x] 2.1 Update runtime launch, join, resume, and relaunch flows to resolve and persist memo-pages memory paths before session publication.
- [x] 2.2 Update session manifest models, schemas, parsing, and serialization from workspace/scratch/persist fields to `memory_root`, `memo_file`, and `pages_dir`.
- [x] 2.3 Update launch-plan environment injection and stable discovery publication to use the new memory env variables only.
- [x] 2.4 Update managed-agent state, detailed-state payloads, renderers, and inspection output to report memory root, memo file, and pages directory.
- [x] 2.5 Decide and implement the supported failure behavior for old manifests that expose only workspace-lane metadata.

## 3. CLI And Profile Surfaces

- [x] 3.1 Replace `houmao-mgr agents workspace` lane commands with memo/page memory commands for path, memo show/set/append, pages list/read/write/append/delete, and reindex.
- [x] 3.2 Remove `--persist-dir` and `--no-persist-dir` from `houmao-mgr agents launch` and `houmao-mgr agents join`.
- [x] 3.3 Remove stored persist fields and persist precedence from launch-profile catalog models, migrations/projections, and explicit launch-profile commands.
- [x] 3.4 Remove persist controls and persist inspection fields from project easy profile and easy instance surfaces.
- [x] 3.5 Update cleanup commands so session cleanup preserves managed memory and scratch-lane cleanup is no longer exposed as a supported operation.

## 4. Gateway And Pair Proxy

- [x] 4.1 Replace gateway workspace lane models with memory summary, memo, page, and reindex request/response models.
- [x] 4.2 Replace live gateway workspace routes with memo/page memory routes that enforce pages-directory containment and fixed memo targeting.
- [x] 4.3 Replace pair-server gateway workspace proxy routes and client methods with memo/page memory proxy routes.
- [x] 4.4 Update gateway service tests for memory summary, memo operations, page read/write/append/delete, reindex, containment failures, and removed lane behavior.

## 5. Skills And Documentation

- [x] 5.1 Update advanced usage pattern skills so mutable loop ledgers no longer use `HOUMAO_AGENT_SCRATCH_DIR` or `HOUMAO_AGENT_PERSIST_DIR`.
- [x] 5.2 Update pairwise-v2 initialization guidance to use the supported memory memo/page surface and `HOUMAO_AGENT_PAGES_DIR` for oversized readable context.
- [x] 5.3 Replace the managed workspace getting-started guide with a managed memory guide for `houmao-memo.md` plus indexed `pages/`.
- [x] 5.4 Update README, docs indexes, launch-profile docs, system-files docs, CLI reference docs, and mailbox boundary docs to remove scratch/persist memory wording.
- [x] 5.5 Update system skill references and packaged prompts that mention removed memory env variables or workspace lane commands.

## 6. Tests And Validation

- [x] 6.1 Update unit tests for memory path resolution, env publication, page containment, memo indexing, and index preservation.
- [x] 6.2 Update CLI tests for launch/join output, memory commands, profile/easy persist-flag removal, and cleanup behavior.
- [x] 6.3 Update runtime, manifest, gateway, and pair-proxy tests for the new memory payload fields and removed workspace lane routes.
- [x] 6.4 Run `pixi run test` and targeted runtime/gateway suites that cover managed launch, join, and gateway memory access.
- [x] 6.5 Run `openspec status --change simplify-agent-memory-pages` and relevant OpenSpec validation before implementation is marked complete.
