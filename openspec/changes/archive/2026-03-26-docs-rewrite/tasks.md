## 1. Stale Content Removal

- [x] 1.1 Delete retired CAO reference docs: `docs/reference/cao_interactive_demo.md`, `docs/reference/cao_server_launcher.md`, `docs/reference/cao_shadow_parser_troubleshooting.md`, `docs/reference/cao_claude_shadow_parsing.md`
- [x] 1.2 Delete the entire `docs/migration/` directory and all its contents (6 files across subdirectories)
- [x] 1.3 Grep all remaining `docs/**/*.md` files for references to deleted filenames and `scripts/demo/` paths; remove or redirect broken links
- [x] 1.4 Grep all remaining `docs/**/*.md` files for `-demo-pack` references and remove demo walkthrough content

## 2. Site Structure and Index

- [x] 2.1 Create `docs/getting-started/` directory
- [x] 2.2 Create new `docs/reference/cli/` directory
- [x] 2.3 Create new `docs/reference/build-phase/` directory
- [x] 2.4 Create new `docs/reference/run-phase/` directory
- [x] 2.5 Create new `docs/reference/tui-tracking/` directory
- [x] 2.6 Create new `docs/reference/lifecycle/` directory
- [x] 2.7 Create new `docs/reference/terminal-record/` directory (move content from existing flat file)
- [x] 2.8 Rewrite `docs/index.md` with new TOC covering getting-started, reference (by phase and subsystem), and developer sections — no CAO, no demos

## 3. Getting Started Section

- [x] 3.1 Write `docs/getting-started/overview.md`: two-phase lifecycle, backend model, high-level architecture — derived from `brain_builder.py` and `realm_controller/` module docstrings
- [x] 3.2 Write `docs/getting-started/agent-definitions.md`: agent definition directory layout (`brains/tool-adapters/`, `skills/`, `cli-configs/`, `api-creds/`, `brain-recipes/`, `roles/`, `blueprints/`) — derived from `tests/fixtures/agents/` structure and `brain_builder.py` model definitions
- [x] 3.3 Write `docs/getting-started/quickstart.md`: build a brain and start a session using `houmao-mgr` commands — derived from `srv_ctrl/commands/` Click groups

## 4. CLI Reference

- [x] 4.1 Write `docs/reference/cli/houmao-mgr.md`: document `admin`, `agents`, `brains`, `server`, `passthrough` command groups and their subcommands — derived from `srv_ctrl/commands/` module docstrings
- [x] 4.2 Write `docs/reference/cli/houmao-server.md`: document `serve`, `health`, `current-instance`, `register-launch`, `sessions`, `terminals` commands — derived from `server/commands/` module docstrings
- [x] 4.3 Write `docs/reference/cli/houmao-passive-server.md`: document registry-driven model, serve command, API surface — derived from `passive_server/` module docstrings; position as CAO-free server path
- [x] 4.4 Add brief deprecation note for `houmao-cli` and `houmao-cao-server` in the CLI reference section (1–2 sentences each, not separate pages)

## 5. Build Phase Reference

- [x] 5.1 Write `docs/reference/build-phase/brain-builder.md`: `BuildRequest` → projection → `BuildResult` workflow — derived from `brain_builder.py` class docstrings and signatures
- [x] 5.2 Write `docs/reference/build-phase/recipes-and-adapters.md`: `BrainRecipe` fields, `ToolAdapter` contract, YAML structure — derived from frozen dataclass definitions
- [x] 5.3 Write `docs/reference/build-phase/launch-overrides.md`: `LaunchDefaults`, `LaunchOverrides`, override scope vs backend-owned params — derived from `agents/launch_overrides/` docstrings

## 6. Run Phase Reference

- [x] 6.1 Write `docs/reference/run-phase/launch-plan.md`: `LaunchPlanRequest` → `build_launch_plan()` → `LaunchPlan` with env resolution, overrides, mailbox bindings — derived from `launch_plan.py`
- [x] 6.2 Write `docs/reference/run-phase/session-lifecycle.md`: `RuntimeSessionController`, start/resume/prompt/stop lifecycle, manifest persistence, job directories — derived from `runtime.py` docstrings
- [x] 6.3 Write `docs/reference/run-phase/backends.md`: `BackendKind` type, per-backend summary (`local_interactive` primary, headless alternatives, CAO-backed legacy) — derived from `models.py` and per-backend module docstrings
- [x] 6.4 Write `docs/reference/run-phase/role-injection.md`: `plan_role_injection()`, per-backend injection methods (Codex → developer instructions, Claude → system prompt + bootstrap, Gemini → bootstrap, CAO → profile-based) — derived from `launch_plan.py`

## 7. Subsystem Reference

- [x] 7.1 Rewrite `docs/reference/gateway/` docs: remove CAO framing, document as session-owned FastAPI sidecar — derived from `gateway_service.py`, `gateway_models.py`, `gateway_storage.py`
- [x] 7.2 Light accuracy pass on `docs/reference/mailbox/` (12 files): verify protocol version, message format, FS layout, Stalwart descriptions match current `mailbox/` source; remove any stale CAO references
- [x] 7.3 Write `docs/reference/tui-tracking/state-model.md`: `TrackedStateSnapshot`, `DetectedTurnSignals`, `CompletionState`, `ProcessState`, `ReadinessState`, `TurnPhase` — derived from `shared_tui_tracking/models.py`
- [x] 7.4 Write `docs/reference/tui-tracking/detectors.md`: `ClaudeCodeSignalDetectorV2_1_X`, `CodexTuiSignalDetector`, `DetectorProfileRegistry`, `app_id_from_tool()` — derived from `shared_tui_tracking/detectors.py` and `registry.py`
- [x] 7.5 Write `docs/reference/tui-tracking/replay.md`: `StreamStateReducer`, `replay_timeline()`, `TuiTrackerSession` — derived from `shared_tui_tracking/reducer.py` and `session.py`
- [x] 7.6 Write `docs/reference/lifecycle/completion-detection.md`: `TurnAnchor`, `ReadinessSnapshot`, `AnchoredCompletionSnapshot`, `build_readiness_pipeline()`, `build_anchored_completion_pipeline()` — derived from `lifecycle/` docstrings
- [x] 7.7 Light accuracy pass on `docs/reference/registry/` (5 files): verify `ManagedAgentRecord`, `LiveAgentRecord`, filesystem registry operations match source; remove stale CAO refs
- [x] 7.8 Move/rewrite terminal record content into `docs/reference/terminal-record/`: recording setup, capture format, replay — derived from `terminal_record/` source
- [x] 7.9 Light accuracy pass on `docs/reference/system-files/` (7 files): verify filesystem layout descriptions match current `owned_paths.py` and runtime home structure

## 8. Developer Guides

- [x] 8.1 Rewrite `docs/developer/tui-parsing/architecture.md`: replace "CAO transport surface" framing with tmux pane capture / headless stdout — derived from `shared_tui_tracking/` and `backends/` source
- [x] 8.2 Rewrite `docs/developer/tui-parsing/index.md` and `runtime-lifecycle.md`: remove CAO lifecycle framing, describe in terms of `StreamStateReducer` and detector profiles
- [x] 8.3 Update `docs/developer/tui-parsing/maintenance.md`: reference `shared_tui_tracking/` detectors and `shared_tui_tracking/apps/` for provider drift procedures
- [x] 8.4 Update `docs/developer/tui-parsing/claude-signals.md` and `codex-signals.md`: remove demo-pack references, ground in detector source code
- [x] 8.5 Update `docs/developer/tui-parsing/shared-contracts.md`, `claude.md`, `codex.md`: remove remaining CAO references
- [x] 8.6 Update `docs/developer/terminal-record/` files: remove CAO references, verify against `terminal_record/` source
- [x] 8.7 Rewrite `docs/developer/houmao-server/` files: document `create_app()`, `HoumaoServerService`, managed agent tracking, gateway proxying — derived from `server/` docstrings; mention CAO child supervision only as legacy

## 9. Cleanup and Existing Reference Rewrites

- [x] 9.1 Rewrite `docs/reference/realm_controller.md` (77 CAO refs): describe multi-backend session model with `local_interactive` as primary — derived from `realm_controller/` source
- [x] 9.2 Rewrite `docs/reference/houmao_server_pair.md`: remove CAO dependency narrative, describe as server + manager pair — derived from `server/` and `srv_ctrl/` docstrings
- [x] 9.3 Rewrite or remove `docs/reference/houmao_server_agent_api_live_suite.md`: update to reference current API without demo-pack walkthrough
- [x] 9.4 Rewrite `docs/reference/realm_controller_send_keys.md`: remove CAO framing if present
- [x] 9.5 Update `docs/reference/managed_agent_api.md`: verify accuracy against `srv_ctrl/commands/managed_agents.py`
- [x] 9.6 Final grep pass: search all `docs/**/*.md` for remaining "CAO" mentions not in legacy/compatibility context; clean up or add legacy qualifier
- [x] 9.7 Final grep pass: search all `docs/**/*.md` for remaining `scripts/demo/` or `-demo-pack` mentions; remove any survivors
