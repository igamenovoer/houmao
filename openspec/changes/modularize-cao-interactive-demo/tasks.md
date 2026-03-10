## 1. Create subpackage scaffold

- [ ] 1.1 Create `src/gig_agents/demo/cao_interactive_demo/` directory with an empty `__init__.py`
- [ ] 1.2 Create `models.py` — extract all Pydantic models (`DemoState`, `TurnRecord`, `ControlInputRecord`, `ControlActionSummary`, `VerificationTurnSummary`, `VerificationReport`, `_StrictModel`), dataclasses (`DemoPaths`, `DemoEnvironment`, `DemoInvocation`, `CommandResult`, `OutputTextTailResult`), type aliases (`CommandRunner`, `ProgressWriter`, `_ModelT`), the `DemoWorkflowError` exception, and all module-level constants from the monolith

## 2. Extract rendering and utility module

- [ ] 2.1 Create `rendering.py` — extract `_render_human_inspect_output`, `_render_start_output`, `_indented_lines`, `_parse_events`, `_extract_done_message`, `_parse_control_action_summary`, `_load_json_file`, `_write_json_file`, `_parse_json_output`, `_require_mapping`, `_require_non_empty_string`, `_validate_model`, `_require_tool`, `_join_command`, `_emit_startup_progress`, `_format_elapsed_seconds`, `_positive_int`, `_print_json`, `_utc_now`. Import models from `.models`

## 3. Extract runtime module

- [ ] 3.1 Create `runtime.py` — extract `run_subprocess_command`, `_run_subprocess_command_with_wait_feedback`, `_build_brain`, `_start_runtime_session`, `_stop_remote_session`, `_looks_like_stale_stop_failure`, `_kill_tmux_session`, `_runtime_cli_command`, `_launcher_cli_command`, `_cao_profile_store`, `_terminal_log_path`, `_resolved_terminal_log_path_for_state`, `_launcher_home_dir_from_cao_profile_store`, `_best_effort_claude_code_state`, `_best_effort_output_text_tail`. Import from `.models` and `.rendering`

## 4. Extract CAO server management module

- [ ] 4.1 Create `cao_server.py` — extract `_write_launcher_config`, `_ensure_cao_server`, `_launcher_status_payload`, `_launcher_start_payload`, `_launcher_status_is_verified_cao_server`, `_parse_command_json_output`, `_prompt_yes_no`, `_replace_existing_cao_server`, `_stop_cao_server_with_known_configs`, `_known_launcher_config_paths`, `_loopback_port_is_listening`, `_fixed_cao_port`, `_find_listening_pids_for_port`, `_list_listening_socket_inodes`, `_find_pids_for_socket_inodes`, `_wait_for_loopback_port_clear`, `_read_process_cmdline`, `_looks_like_cao_server_cmdline`, `_terminate_process`, `_wait_for_process_exit`. Import from `.models` and `.rendering` and `.runtime`

## 5. Extract commands module

- [ ] 5.1 Create `commands.py` — extract the public lifecycle functions `start_demo`, `send_turn`, `send_control_input`, `inspect_demo`, `verify_demo`, `stop_demo`, plus state I/O helpers `load_demo_state`, `save_demo_state`, `load_turn_records`, `load_control_records`, `require_active_state`, and workspace helpers `_ensure_workspace`, `_reset_demo_artifacts`, `_provision_default_worktree`, `_reset_demo_startup_state`, `_load_previous_demo_state`, `_mark_state_inactive`, `_next_turn_index`, `_next_control_index`, `_read_current_run_root`, `_write_current_run_root`, `_latest_demo_run_root`, `_run_timestamp_slug`. Import from `.models`, `.rendering`, `.runtime`, `.cao_server`

## 6. Extract CLI module

- [ ] 6.1 Create `cli.py` — extract `main`, `_build_parser`, `_resolve_demo_invocation`, `_resolve_repo_root`, `_resolve_workspace_root`, `_resolve_prompt_text`, `_resolve_key_stream`. Import from `.models` and `.commands`

## 7. Wire up package exports and migrate callers

- [ ] 7.1 Populate `cao_interactive_demo/__init__.py` with explicit `__all__` re-exporting every public symbol from the six modules
- [ ] 7.2 Remove `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` after the package exports are in place
- [ ] 7.3 Update repository-owned CLI wrappers and helpers to the split package: change `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh` to invoke `pixi run python -m gig_agents.demo.cao_interactive_demo.cli`, update `scripts/demo/cao-interactive-full-pipeline-demo/scripts/verify_report.py`, and refresh README references to the deleted module path
- [ ] 7.4 Rename `tests/unit/demo/test_cao_interactive_full_pipeline_demo.py` to `tests/unit/demo/test_cao_interactive_demo.py`, update its imports to `gig_agents.demo.cao_interactive_demo`, and retarget monkeypatches to the owning submodules (`cao_server`, `commands`, `runtime`, `cli`)
- [ ] 7.5 Rename `tests/integration/demo/test_cao_interactive_full_pipeline_demo_cli.py` to `tests/integration/demo/test_cao_interactive_demo_cli.py` and update its imports, module invocation assertions, and helper expectations to the split package path

## 8. Validation

- [ ] 8.1 Add a focused unit test covering canonical package imports and explicit `gig_agents.demo.cao_interactive_demo.__all__`
- [ ] 8.2 Run `pixi run typecheck` and fix any import or type errors in the new subpackage and migrated callers
- [ ] 8.3 Run `pixi run lint && pixi run format` and fix any style issues
- [ ] 8.4 Run `pixi run test` to confirm unit tests pass against the new package path
- [ ] 8.5 Run `pixi run pytest tests/integration/demo/test_cao_interactive_demo_cli.py` to confirm the CLI migration works end-to-end
- [ ] 8.6 Verify `pixi run python -m gig_agents.demo.cao_interactive_demo.cli --help` works
