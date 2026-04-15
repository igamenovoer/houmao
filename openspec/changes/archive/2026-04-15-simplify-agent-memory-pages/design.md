## Context

The current managed-agent memory subsystem is the result of two recent broadening steps. First, Houmao added an optional durable memory directory. Then it unified job scratch and durable memory into a managed workspace envelope:

```text
<active-overlay>/memory/agents/<agent-id>/
  houmao-memo.md
  scratch/
  persist/
```

That envelope solved path discoverability, but it also made Houmao responsible for a generic per-agent file workspace. In practice, this overstates Houmao's role. Claude, Codex, and similar tools already maintain sophisticated internal memory or context behavior, while real work artifacts are usually better kept in the launched working directory, a project artifact directory, mailbox state, or an explicit operator-selected path. Houmao's useful role is narrower: provide one stable, operator-visible memo surface for live-agent instructions and small durable notes.

The new model is intentionally breaking. The repository is still unstable, and the preferred direction is to simplify the contract rather than preserve scratch/persist compatibility.

## Goals / Non-Goals

**Goals:**
- Replace the broad workspace-lane model with a small managed-agent memory notebook.
- Keep the default root stable at `<active-overlay>/memory/agents/<agent-id>/`.
- Ensure each memory root contains only `houmao-memo.md` and one managed subdirectory named `pages/`.
- Make `houmao-memo.md` the stable entrypoint and managed index for page content.
- Publish simple live env variables: `HOUMAO_AGENT_MEMORY_DIR`, `HOUMAO_AGENT_MEMO_FILE`, and `HOUMAO_AGENT_PAGES_DIR`.
- Persist the simplified memory paths in session-owned runtime state for relaunch, join, inspection, gateway attach, and offline debugging.
- Provide supported CLI, gateway, and pair-server operations for memo and page files.
- Keep page file operations path-contained and avoid arbitrary memory-root writes.

**Non-Goals:**
- No scratch workspace, generic artifact store, durable persist lane, or shared external memory binding.
- No compatibility aliases for `HOUMAO_AGENT_STATE_DIR`, `HOUMAO_AGENT_SCRATCH_DIR`, `HOUMAO_AGENT_PERSIST_DIR`, `--persist-dir`, or `--no-persist-dir`.
- No automatic migration of existing `scratch/` or `persist/` contents.
- No embedding of Claude/Codex internal memory behavior into Houmao.
- No indexing/search database, vector store, sync engine, or semantic retrieval service.
- No fixed taxonomy inside `pages/` beyond path containment and memo index generation.

## Decisions

### Decision: Treat managed memory as a memo-pages notebook

Default layout:

```text
<active-overlay>/memory/agents/<agent-id>/
  houmao-memo.md
  pages/
```

`houmao-memo.md` is the first file humans and agents open. It may contain freeform top-level notes, but it also owns one managed index section listing pages under `pages/`.

Rationale: the visible product concept becomes easy to explain. Houmao provides a small notebook, not a second workdir, a scratch area, or a replacement for provider memory.

Alternative considered: keep `scratch/` and rename `persist/` to `pages/`. Rejected because it keeps the generic workspace abstraction alive and leaves agents guessing which filesystem lane should hold task state.

### Decision: Store page content as contained text files under `pages/`

Supported page operations address paths relative to `pages/`. Paths must be relative, must reject `..`, must remain inside `pages/` after symlink resolution, and should prefer Markdown page files. Houmao should not permit arbitrary writes beside `houmao-memo.md` at the memory root.

Rationale: page files are simple enough for agents and operators to inspect directly, while containment keeps gateway and pair-server routes from becoming broad filesystem APIs.

Alternative considered: store pages in a catalog table. Rejected because filesystem Markdown pages are easier to inspect, edit, back up, and use from live CLI agents.

### Decision: Let `houmao-memo.md` index pages, not duplicate them

Supported page mutations refresh a bounded managed index section in `houmao-memo.md`, for example:

```markdown
## Pages
<!-- houmao-pages-index:start -->
- [operator-rules](pages/operator-rules.md): Standing constraints for this agent.
- [loop-contexts/run-20260414](pages/loop-contexts/run-20260414.md): Current loop context.
<!-- houmao-pages-index:end -->
```

The page body remains authoritative in `pages/`. The memo index is a navigational summary and should be rebuildable with a reindex operation.

Rationale: copying full page content into the memo creates two sources of truth. A generated index keeps the memo useful without making it a database.

Alternative considered: append every page body to `houmao-memo.md`. Rejected because large memo files become hard to scan and stale copies are likely.

### Decision: Remove persist binding entirely from launch/profile surfaces

Launch and profile surfaces should stop accepting or storing `--persist-dir`, `--no-persist-dir`, `persist_dir`, `persist_disabled`, and `persist_binding`. Work artifacts and shared durable directories are outside this memory subsystem and should be represented by the launched working directory, user instructions, project-local paths, or future explicit artifact configuration if needed.

Rationale: keeping an exact external persist binding under a renamed memory model would preserve the main confusion. Houmao memory is not the user's project artifact store.

Alternative considered: keep exact path binding but bind it to the memory root. Rejected because exact binding invites shared arbitrary state and conflicts with the requirement that Houmao-owned memory has exactly one `pages/` subdirectory.

### Decision: Replace workspace APIs with memo/page APIs

CLI and gateway surfaces should move from lane verbs to notebook verbs. The exact command names can be finalized during implementation, but the supported operations are:

- resolve memory paths,
- read, replace, and append the fixed memo,
- list pages,
- read one page,
- write or append one page,
- delete one page,
- reindex `houmao-memo.md` from current `pages/` contents.

The pair server should proxy the same live gateway memory operations for managed agents it resolves.

Rationale: the control plane should make the intended use case obvious. A generic `workspace lane write` API suggests arbitrary state management; a page API suggests small notes.

Alternative considered: keep old route names and only restrict lanes internally. Rejected because it leaves the wrong public vocabulary in place.

### Decision: Move loop bookkeeping out of Houmao memory by default

Advanced usage patterns must stop telling agents to store mutable ledgers under `HOUMAO_AGENT_SCRATCH_DIR`. When a pattern needs durable, operator-visible context, it may write a readable page under `pages/`. When it needs retry counters, dedupe state, mailbox receipts, or live supervision state, it should use the mailbox, reminder, runtime, or pattern-specific mechanism rather than treating managed memory as a mutable database.

Rationale: otherwise `pages/` becomes scratch under another name.

Alternative considered: store JSON ledgers under `pages/`. Rejected because it preserves the old scratch-lane behavior and makes the page notebook less legible.

## Risks / Trade-offs

- [Risk] Existing scripts, docs, and tests that rely on scratch/persist names will break. -> Accept as deliberate breakage and update all in-repo surfaces in one implementation.
- [Risk] Users may still need a place for large artifacts. -> Document that artifacts belong in the launched workdir or explicit project paths, not Houmao memory.
- [Risk] Direct filesystem edits under `pages/` can make the memo index stale. -> Provide a `reindex` operation and make supported page mutations refresh the managed index automatically.
- [Risk] Removing scratch may leave advanced loop patterns without a default ledger home. -> Revise those patterns to use mailbox/reminder/runtime mechanisms or readable pages only for operator-visible context.
- [Risk] Old manifest payloads may contain only workspace fields. -> For this breaking change, implementation may either reject old workspace-aware manifests with a clear error or derive best-effort memory paths only where needed for inspection; it must not keep publishing old env contracts.
- [Trade-off] Markdown pages are less structured than a database. -> This is intentional; the subsystem optimizes for clarity, inspectability, and low conceptual weight.

## Migration Plan

1. Introduce the simplified memory path model and page helpers.
2. Update runtime manifest models, schemas, launch-plan env injection, launch, join, resume, and relaunch flows to use `memory_root`, `memo_file`, and `pages_dir`.
3. Remove persist binding from direct launch, join, project launch-profile, easy profile, and catalog projection surfaces.
4. Replace CLI/gateway/pair-server workspace lane operations with memo/page operations.
5. Update loop skills, docs, specs, renderers, and tests.
6. Run focused unit coverage first, then runtime/gateway coverage for launch, join, and live gateway memory access.

Rollback is a code rollback only. Already-created `pages/` directories and `houmao-memo.md` files can remain ordinary filesystem state.

## Open Questions

None for the proposal. Command and route names can be finalized during implementation as long as they preserve the memo/page contract and remove the lane vocabulary from supported surfaces.
