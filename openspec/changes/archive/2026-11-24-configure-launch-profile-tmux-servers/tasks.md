# Tasks

## 1. Project Profile Selection

- [x] 1.1 Add the typed `defaults.posture.tmux` selector to the shared profile model, catalog, and YAML projection. Verify round-trip of all four modes and rejection of missing, relative, or inapplicable socket paths.
- [x] 1.2 Add `--tmux-server`, `--tmux-socket-path`, and set-time `--clear-tmux-server` to the specialist-backed and recipe-backed project profile commands. Verify create, get, projection, omitted patch, replacement, and clear using both lanes. Document authoring in the launch profiles guide and CLI reference.

## 2. Owner Socket Resolution and Registry

- [x] 2.1 Implement owner-local socket resolution in `houmao.execution` with a concrete path and startup permission. Verify native default selection against an isolated `TMUX_TMPDIR`, legacy scope ordering when omitted, unique private allocation for `new`, and owner-local validation of `socket`.
- [x] 2.2 Implement the versioned owner-level default record in the effective registry using private paths and atomic publication. Verify first and concurrent initialization, stable address derivation across projects and empty registry roots, separation by owner or socket domain, malformed and unsafe record failures, read-only behavior, and survival of agent registry cleanup. Document the shared record and lazy reuse in the execution-context reference.
- [x] 2.3 Pass startup permission through the shared tmux adapter, including connect-only session creation with the curated environment. Verify on isolated sockets that a cold Houmao default starts at the selected address, concurrent sessions share it, and an existing-only selection cannot start a replacement server if it loses the preflight race.

## 3. Managed Birth and Relaunch

- [x] 3.1 Add the one-shot project launch flags and forward them through delegated launch. Resolve the selector once before force takeover, enforce the admitted executor’s fixed socket, and protect same-server existing-only replacements. Verify direct/profile/fallback precedence, profile immutability, owner-context validation, and predecessor preservation on preflight failure. Add precedence and error examples to the CLI reference.
- [x] 3.2 Feed the accepted selection to managed backend startup and save the concrete socket and startup permission in the runtime binding. Use that binding for subsequent control and relaunch. Verify saved-socket operations with overlapping coordinates on a second isolated server, relaunch after a profile edit, and cold relaunch under both start-permitted and existing-only bindings.

## 4. Fixture Launch and Lifecycle

- [x] 4.1 Make `fixture.py prepare` select `houmao-default` for local tmux-backed runs, with `--tmux-server new` for isolation. Use a stored profile for managed launch and verify it contains both the chosen socket mode and any configured model or reasoning defaults. Verify preparation leaves the server untouched and raw headless and passive paths retain their existing routing. Update the fixture README with the new default, isolation flag, and cleanup behavior.
- [x] 4.2 Resolve raw TUI and Web launch through the shared selector and use the curated startup environment. Capture the managed manifest socket or exact raw terminal coordinates and verify run ownership for follow-up and partial startup cleanup. Verify two ordinary managed fixtures with independent registries share a test-owned default, one can stop while the other remains usable, raw credentials stay out of shared tmux state, and an already-live isolated fixture still targets its recorded session.
- [x] 4.3 Migrate tmux fixture tests to explicitly isolated resources. Preserve peer discovery, mail and gateway checks under a test-owned socket-restricting shim, and direct prompt with an authorized route and detached gateways. Verify with `tests/integration/agents/test_record_backed_peer_operations.py` using synthetic inputs on two `new` servers.

## 5. Integration Verification

- [x] 5.1 Run relevant profile, execution, registry, runtime, and fixture tests through Pixi, including real-tmux integration on explicitly isolated socket paths with `TMUX` and `TMUX_PANE` cleared. Run strict OpenSpec validation for the change.
