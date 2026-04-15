## Why

The managed-memory change made `houmao-memo.md` a partly generated file by inserting and refreshing a page index. That conflicts with the intended model: the memo is supposed to be a free-form Markdown notebook edited directly by a user or LLM.

This change corrects that ownership boundary before the memory model is archived into the main specs.

## What Changes

- **BREAKING** Treat `houmao-memo.md` as fully user/LLM-owned free-form Markdown.
- **BREAKING** Remove all generated page-index behavior, including automatic memo mutation on page writes/deletes and explicit reindex operations.
- Add supported path-discovery behavior that returns full absolute paths and memo-friendly relative links for pages under `pages/`.
- Keep contained page read/write/list/delete behavior under `pages/`, but make page mutations independent from memo content.
- Update CLI, gateway, pair-server, and passive-server memory APIs so callers can resolve page paths without relying on a generated memo index.
- Update docs and packaged skills to describe memo links to `pages/...` as user-authored or LLM-authored references.
- Do not implement migration behavior. Existing memo content, including any old generated marker block, is ordinary Markdown after this change.

## Capabilities

### New Capabilities
- `agent-memory-freeform-memo`: Defines the corrected free-form memo contract, page path discovery, no generated index, and no migration behavior.

### Modified Capabilities
- `agent-gateway`: Remove gateway memory reindex behavior and add page path-resolution responses with full paths.
- `passive-server-gateway-proxy`: Proxy the corrected memory path-resolution surface and stop proxying reindex.
- `docs-getting-started`: Describe managed memory as a free-form memo plus optional pages without generated indexes.
- `system-files-reference-docs`: Document memo/page ownership and path-discovery semantics.
- `houmao-agent-loop-pairwise-v2-skill`: Update initialization guidance to treat memo/page links as authored content, not generated index entries.

## Impact

- Affects `src/houmao/agents/agent_workspace.py`, gateway memory models/service/client routes, server/passive proxy memory routes, and `houmao-mgr agents memory` commands.
- Removes public `reindex` CLI/API behavior from the memory surface.
- Updates tests that currently assert memo index generation, page mutation index refresh, and reindex actions.
- Updates README, docs, OpenSpec specs, and packaged system-skill guidance that currently mention indexed pages as Houmao-generated memo content.
