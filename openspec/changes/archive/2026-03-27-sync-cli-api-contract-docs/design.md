## Context

The repository already has strong subsystem documentation, but the operator-facing path has drifted from the live implementation. The verified gaps cluster in three places:

- getting-started docs still show older managed-agent flows built around `--manifest`, `--session-id`, and `agents terminate`,
- CLI reference pages do not fully reflect the current `houmao-mgr` and `houmao-server` command trees,
- runtime, agent, gateway, and mailbox reference pages contain specific stale claims about lifecycle, raw control input, attach discovery, and live mailbox endpoint resolution.

This is a cross-cutting documentation change that spans multiple existing documentation capabilities rather than one isolated page. The change is documentation-only, but it still needs a design because it touches multiple reference subtrees, existing OpenSpec documentation capabilities, and several different code surfaces that act as the source of truth.

The authoritative implementation surfaces for this change are the live Click/FastAPI command trees and the runtime helper modules under `src/houmao/srv_ctrl/commands/`, `src/houmao/server/`, `src/houmao/agents/realm_controller/`, and `src/houmao/agents/mailbox_runtime_support.py`.

## Goals / Non-Goals

**Goals:**

- Make the getting-started path teach the currently supported `houmao-mgr` workflow.
- Make CLI reference pages match the live command and flag surfaces.
- Remove or rewrite stale runtime/reference claims that now conflict with code.
- Add formal, linkable CLI reference coverage for newer managed-agent command families.
- Improve cross-links so overview, CLI, API, and subsystem docs point readers to the right depth of detail.

**Non-Goals:**

- Change runtime behavior, API behavior, or command semantics.
- Redesign the entire docs site structure beyond the pages needed for this sync.
- Turn deprecated compatibility surfaces into primary documentation again.
- Exhaustively document every internal or historical command path with equal prominence.

## Decisions

### 1. Use live command surfaces and implementation modules as the documentation source of truth

The update will be driven from current Click help, route definitions, and runtime helpers rather than from existing prose pages. This avoids carrying forward already-stale terminology or examples.

Alternative considered: patch the existing docs incrementally using only nearby prose as context. Rejected because several of the current pages already copy stale assumptions from each other.

### 2. Re-center operator-facing docs on the current managed-agent workflow

The top-level reader path will be updated to emphasize the current managed-agent flow: selector-based `houmao-mgr agents launch`, managed-agent targeting by `--agent-name` or `--agent-id`, and `agents stop` for shutdown. Older manifest/session-id examples can still exist in narrowly scoped compatibility pages when needed, but they will not remain the primary recommended path.

Alternative considered: keep both old and new flows side by side in quickstart pages. Rejected because it increases ambiguity for new readers and makes unsupported-looking paths appear equally primary.

### 3. Add dedicated CLI reference pages for complex nested command families

`houmao-mgr.md` will remain the entrypoint, but complex nested command families will gain dedicated pages: `agents gateway`, `agents turn`, `agents mail`, `agents mailbox`, and `admin cleanup`. This keeps the CLI reference navigable while giving newer command families formal, linkable homes.

Alternative considered: expand `houmao-mgr.md` into one very large page with every subcommand table inline. Rejected because that would make one page harder to scan and harder to maintain.

### 4. Update cross-linked reference pages in place instead of creating transitional docs

Existing getting-started, run-phase, agent, gateway, and mailbox pages will be corrected in place. The change will rely on better cross-links between overview pages and detailed CLI/subsystem pages rather than adding temporary migration notes.

Alternative considered: create a separate “docs drift” note that explains the current truth while leaving stale pages intact. Rejected because it preserves contradictory documentation and forces readers to discover the correction manually.

### 5. Keep legacy compatibility information, but demote it to explicit compatibility or troubleshooting context

Deprecated runtime-local and CAO-backed surfaces will still be documented where they remain relevant for compatibility or troubleshooting, but those pages will clearly mark them as legacy and will not describe them as the default operator path.

Alternative considered: remove all legacy mention from the docs update. Rejected because some compatibility surfaces still exist and some troubleshooting pages remain useful.

## Risks / Trade-offs

- **Cross-page inconsistency while editing multiple doc trees** → Mitigation: use the same source-of-truth code surfaces and terminology across CLI, runtime, agent, gateway, and mailbox pages, then do a final stale-string sweep.
- **More CLI reference pages can increase navigation surface area** → Mitigation: keep `houmao-mgr.md` as the entrypoint and add explicit cross-links from `docs/reference/index.md` and relevant API/reference pages.
- **Demoting older flows may surprise readers who still use compatibility paths** → Mitigation: retain narrowly scoped legacy notes and troubleshooting docs where those flows still exist, but label them clearly.
- **Future command drift can recur** → Mitigation: ensure updated pages cite the implementation files they reflect and anchor command details to live help and command modules.

## Migration Plan

1. Update the getting-started docs so the primary reader journey is correct.
2. Correct stale CLI and runtime reference claims in existing pages.
3. Add dedicated CLI reference pages for the nested managed-agent command families.
4. Update indexes and cross-links so readers can discover the new pages from existing overviews and API docs.
5. Validate the final result with targeted searches for stale strings such as `--session-id`, `agents terminate`, `join-tmux`, and job-dir manifest claims.

This is a documentation-only migration. There is no runtime data migration, deployment sequence, or rollback mechanism beyond reverting the doc changes.

## Open Questions

- Should this same change update `README.md` examples, or should README alignment be handled as a follow-up once the deeper docs are merged?
- Are there any passive-server or other compatibility reference pages that should be opportunistically aligned in this same pass if they share the same stale CLI wording?
