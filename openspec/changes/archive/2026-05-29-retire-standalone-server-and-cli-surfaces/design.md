## Context

Houmao now has two maintained operator/API directions:

- `houmao-mgr` owns local project, agent-definition, launch, join, mailbox, credential, cleanup, and system-skill workflows.
- `houmao-passive-server` owns API-based discovery, observation, request submission, gateway proxying, mailbox proxying, and managed-headless management for running Houmao agents.

The older standalone `houmao-server` executable and deprecated `houmao-cli` realm-controller surface still appear in packaging, docs, tests, and specs. That creates ambiguity about which server users should run and leaves the project maintaining two server identities. At the same time, several useful implementation modules currently live under `houmao.server` and are consumed by maintained code, especially passive-server compatibility models, managed-headless store records, pair-client normalization, and TUI observation helpers.

## Goals

- Remove `houmao-server` and `houmao-cli` from packaged executable scripts.
- Remove `houmao-mgr server ...` as a maintained manager command group.
- Make `houmao-passive-server` the only maintained server executable and API authority.
- Keep `houmao-mgr` working for local workflows after the server group is removed.
- Preserve useful old-server Python modules as internal/shared implementation support when maintained surfaces still depend on them.
- Move or re-home old-server-owned managed-agent behavior into passive-server where it is still needed.
- Update docs, specs, and tests so they no longer describe `houmao-server`, `/cao/*`, `houmao_server_rest`, or `houmao-cli` as supported public operator surfaces.

## Non-Goals

- Delete every module under `src/houmao/server/` in one change.
- Preserve backward compatibility for the removed executables or the removed `houmao-mgr server` command group.
- Keep standalone `/cao/*` server compatibility as a public promise.
- Introduce a second passive-server API shape just to mimic old `houmao-server` route names when passive-server already has maintained routes.

## Decisions

### Packaging

`pyproject.toml` keeps packaged scripts for `houmao-mgr` and `houmao-passive-server` only. The `houmao-server = "houmao.server.cli:main"` and `houmao-cli = "houmao.cli:main"` entries are removed.

### Manager CLI

`houmao-mgr` keeps the local command families users still rely on, but it stops registering the top-level `server` group. Files whose only purpose is launching or controlling the standalone server, such as the old manager server command module and detached startup helper, can be removed once imports and tests are cleaned up.

Existing manager commands that talk to a managed API should resolve a supported pair authority through the maintained client factory and prefer passive-server semantics. Labels may still say "server" as a generic target mode when the code path supports a remote API authority, but user-facing help must not require `houmao-server` specifically unless it is historical/internal text.

### Server API Ownership

`houmao-passive-server` becomes the maintained API authority for agent management. Behavior that is still useful from the old managed-agent API should live in passive-server modules or neutral shared modules and be exposed through passive-server routes.

Old `/cao/*`, terminal-keyed standalone server extension routes, `houmao_server_rest`, and old server lifecycle routes are retired as public contracts. Existing internal adapters may remain during refactoring when maintained code still imports them, but tests should not assert them as public executable behavior.

### Internal Module Retention

The package name `houmao.server` no longer implies a supported standalone product. During this transition it may continue to host shared models, clients, managed-headless records, parser adapters, process/tmux helpers, or compatibility code used by `houmao-mgr` and `houmao-passive-server`.

When a retained module is broadly shared and no longer server-specific, a later cleanup may move it to a neutral package. This change only requires that public packaging, docs, and tests stop treating the old server executable/API as maintained.

### Documentation and Tests

CLI reference docs stop listing `houmao-server` and `houmao-cli` as installable commands. Passive-server docs become the maintained server reference. Old server developer docs may either be removed or rewritten as internal implementation notes that do not tell users to run `houmao-server`.

Tests should be reshaped around maintained behavior:

- packaging/help tests assert only retained scripts and command groups;
- `houmao-mgr server` tests are removed or replaced by passive-server/client tests;
- old server CLI and live HTTP-contract tests are removed unless they validate a retained internal helper used by maintained code;
- passive-server tests cover API behavior that moved from old server ownership.

## Risks and Trade-offs

- Removing executable compatibility is breaking, but the repository is in active unstable development and the user-facing path has already shifted to `houmao-mgr` plus `houmao-passive-server`.
- Keeping some `houmao.server` modules temporarily can look untidy, but it avoids a high-risk mechanical move while still removing the unsupported public surface.
- Some docs/specs outside the direct CLI/API specs may still mention old server internals. Implementation should update user-facing references now and leave internal module naming cleanup for a follow-up when it is not on the critical path.

## Migration Plan

1. Remove packaged `houmao-server` and `houmao-cli` console scripts.
2. Remove `houmao-mgr server` registration and standalone lifecycle/session command implementation.
3. Route maintained API/client usage toward `houmao-passive-server` and ensure passive-server owns any still-needed managed-agent operations.
4. Prune or rewrite docs and examples to show `houmao-mgr` and `houmao-passive-server` as the active surfaces.
5. Update tests to remove public old-server/CLI assertions and keep coverage for retained internal helpers only where maintained surfaces depend on them.
