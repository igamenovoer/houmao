## 1. Packaging and CLI Surface

- [x] 1.1 Remove `houmao-server` and `houmao-cli` from `[project.scripts]` while keeping `houmao-mgr` and `houmao-passive-server` packaged.
- [x] 1.2 Remove the top-level `houmao-mgr server` command registration and clean up imports so `houmao-mgr --help` lists only retained command groups.
- [x] 1.3 Remove or internalize manager-only standalone server lifecycle files such as detached old-server startup and `srv_ctrl` server command modules when no retained command imports them.
- [x] 1.4 Remove or internalize standalone old-server Click entrypoint modules so the repository no longer maintains `houmao-server` as a runnable CLI product.
- [x] 1.5 Remove or retire public `houmao-cli` entrypoint behavior and make any retained realm-controller helpers internal rather than user-facing.

## 2. Passive-Server API Ownership

- [x] 2.1 Update pair-authority client resolution so maintained user-facing flows accept `houmao-passive-server` and reject standalone `houmao-server` with explicit retirement guidance.
- [x] 2.2 Update manager commands that use a remote managed API to default to passive-server authority and port semantics where a server authority is required.
- [x] 2.3 Move or expose any still-needed old-server managed-agent operations through `houmao-passive-server` routes or passive-server-aware client methods.
- [x] 2.4 Keep reusable old-server models, managed-headless records, TUI helpers, and compatibility helpers importable only where maintained manager/passive-server code still needs them.
- [x] 2.5 Remove active reliance on `/cao/*`, terminal-keyed old-server extension routes, and old-server lifecycle routes from maintained manager/passive-server paths.

## 3. Runtime Backend Cleanup

- [x] 3.1 Stop creating new runtime manifests with `backend = "houmao_server_rest"` and reject new user-facing selections with migration guidance.
- [x] 3.2 Remove public runtime CLI paths that create or control standalone `cao_rest` sessions through `houmao-cli`.
- [x] 3.3 Update launch-policy and launch-override handling to reference maintained runtime-managed backends instead of `houmao_server_rest`.
- [x] 3.4 Preserve local/headless/joined runtime behavior used by `houmao-mgr` after removing old REST-backed session control.

## 4. Documentation and Guidance

- [x] 4.1 Update CLI reference docs and navigation so active entrypoint tables list `houmao-mgr` and `houmao-passive-server`, not `houmao-server` or `houmao-cli`.
- [x] 4.2 Remove active `docs/reference/cli/houmao-server.md` coverage or rewrite it as non-user-facing internal history outside the active CLI reference.
- [x] 4.3 Rewrite `docs/reference/cli/houmao-passive-server.md` as the maintained server API reference with serve options, API route families, and manager compatibility notes.
- [x] 4.4 Scan README, AGENTS/instruction files, docs, packaged skills, and examples for active `houmao-server`, `houmao-cli`, `houmao-mgr server`, `/cao/*`, and `houmao_server_rest` guidance and rewrite it as passive-server, manager, historical, or internal-only text.
- [x] 4.5 Update developer docs that still describe old-server internals so they do not instruct users to run a standalone `houmao-server` executable.

## 5. Tests

- [x] 5.1 Update CLI shape and packaging tests to assert that `houmao-server`, `houmao-cli`, and `houmao-mgr server` are absent while retained commands still work.
- [x] 5.2 Remove or rewrite tests that assert standalone old-server CLI, `/cao/*`, old server session lifecycle, or `houmao_server_rest` as public behavior.
- [x] 5.3 Keep focused unit coverage for retained internal helpers under `houmao.server` only when maintained `houmao-mgr` or `houmao-passive-server` paths import them.
- [x] 5.4 Add or adjust passive-server tests for any managed-agent, gateway, mailbox, or headless behavior migrated from old server ownership.

## 6. Verification

- [x] 6.1 Run `pixi run format`.
- [x] 6.2 Run `pixi run lint`.
- [x] 6.3 Run `pixi run typecheck`.
- [x] 6.4 Run `pixi run test`.
- [x] 6.5 Run `pixi run build-dist` and inspect generated entrypoints or metadata to confirm only retained executables are packaged.
