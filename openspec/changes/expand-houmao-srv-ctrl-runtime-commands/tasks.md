## 1. Expand the managed-agent server contract

- [x] 1.1 Add managed-agent API models for gateway request submission and pair-owned mail operations.
- [x] 1.2 Extend `houmao-server` service logic so managed-agent stop supports both TUI and headless agents through one route, with TUI stop using the existing pair-managed session-delete lifecycle.
- [x] 1.3 Add `houmao-server` routes and client helpers for managed-agent gateway request proxying and managed-agent mail status, check, send, and reply operations through an attached live gateway.
- [x] 1.4 Add server tests for TUI stop, missing-live-gateway rejection, and missing-mail-capability rejection.

## 2. Add the native `houmao-srv-ctrl` command groups

- [x] 2.1 Wire `agents`, `brains`, and `admin` into the top-level `houmao-srv-ctrl` command tree while preserving `launch`, `install`, and `cao` and removing the public top-level `agent-gateway` group.
- [x] 2.2 Add shared CLI helpers for managed-agent reference handling, prompt input parsing, JSON rendering, and pair base-URL resolution.
- [x] 2.3 Retire the top-level `agent-gateway` command family and migrate any repo-owned CLI references to `agents gateway ...`.
- [x] 2.4 Implement the `agents` command family as a `src/houmao/srv_ctrl/commands/agents/` sub-package with per-subgroup modules rather than one oversized module.

## 3. Implement the `agents` command family

- [x] 3.1 Add `agents list`, `show`, `state`, `history`, `prompt`, `interrupt`, and `stop` over the managed-agent server APIs, with `show` using the managed-agent detail view and `state` using the operational summary view.
- [x] 3.2 Add `agents gateway attach`, `detach`, `status`, `prompt`, and `interrupt` over the managed-agent gateway APIs and document `agents prompt` as the default prompt path.
- [x] 3.3 Add `agents mail status`, `check`, `send`, and `reply` over the pair-owned managed-agent mail APIs.
- [x] 3.4 Add `agents turn submit`, `status`, `events`, `stdout`, and `stderr` over the managed headless turn APIs with explicit TUI-agent rejection handling.

## 4. Implement the local native command families

- [x] 4.1 Add `brains build` as a local wrapper over the existing brain-build artifact workflow, with a command argument surface aligned to `BuildRequest` rather than a verbatim mirror of every legacy `houmao-cli build-brain` convenience flag.
- [x] 4.2 Add `admin cleanup-registry` as a local wrapper over the existing shared-registry cleanup workflow.
- [x] 4.3 Update command help text so server-backed versus local authority is explicit for each native family.

## 5. Update docs and verify behavior

- [x] 5.1 Audit repo-owned docs under `docs/` and replace `houmao-cli` usage with `houmao-srv-ctrl` wherever the new native pair surface covers the workflow, while keeping `houmao-cli` only for uncovered or intentionally runtime-local workflows.
- [x] 5.2 Update pair CLI reference, gateway operations docs, history and retention docs, and migration docs to document the new native `houmao-srv-ctrl` tree, remove repo-owned `agent-gateway` usage, make `houmao-srv-ctrl` the primary documented command surface for covered pair workflows, and explain what managed-agent history remains in memory versus on disk for long-running tasks.
- [x] 5.3 Add CLI tests for help output, command routing, retirement of `agent-gateway`, and representative success and failure cases.
- [x] 5.4 Run targeted server and CLI tests plus any required spec validation for the expanded native command tree.
