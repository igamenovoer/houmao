# DSH RC2 Per-Turn ACP Acceptance Map

This map tracks all 61 delta scenarios in `dsh-01-add-acp-headless-backend`. Each row identifies executed evidence and its limits. Hermetic and controlled-native results are distinct from real-provider qualification. The explicitly selected DeepSeek Messages manager lane now passes tool completion, exact resume, usage, interruption, and two-home isolation. Real self-hosted qualification remains `not_run` because no compatible deployment/model was selected.

After the Web implementation, the combined regression gate passed 4,150 unit tests with 14 skipped and all 84 native cases, including the 17 headless predecessors. The [Web acceptance map](dsh-web-acceptance.md) records the separate seven-check real-provider Web smoke. Change 01's strict validation remains tied to its SHA-verified captured 240-spec predecessor baseline, where it has zero issues. Current-main strict comparison reports one historical full-block mismatch because change 02 added a Web qualification scenario to that shared fixture requirement. The original 61 scenarios and accepted scope remain unchanged.

## Evidence Layers

- **Transport:** Hermetic real-subprocess tests in `tests/unit/agents/realm_controller/test_dsh_acp_connection.py` and `test_dsh_acp_driver.py`.
- **Native:** Actual identified DSH `0.2.2-rc.3` with controlled local Messages/Chat endpoints in `tests/integration/agents/dsh/`. These runs use synthetic credentials and qualify native contracts without paid provider calls.
- **Accounting:** Sanitized journal fixtures and collector/finalizer regressions; no external provider is implied.
- **Managed:** Runtime, gateway, manager, passive-server, and plugin integration qualification.
- **Live:** Explicit DeepSeek provider smoke; self-hosted lanes require their own configured prerequisites.

The test and command names below refer to the RC2 implementation. The [current headless reference](dsh-headless.md) describes the native one-shot CLI. The historical native tmux tests cleared inherited `TMUX` and `TMUX_PANE` and confined cleanup to their private sockets.

## Evidence Index

Transport and lifecycle test names resolve under `tests/unit/agents/realm_controller/`: `test_dsh_acp_connection.py`, `test_dsh_acp_driver.py`, `test_dsh_lifecycle.py`, `test_dsh_companion.py`, and `test_dsh_gateway_admission.py`. Gateway shared-contract cases are in `test_gateway_support.py` and `test_gateway_manifest_preservation.py`; their DSH parameter cases are named explicitly below.

Configuration and fixture cases are in `tests/unit/agents/test_dsh_configuration.py`, `test_dsh_launch_surfaces.py`, `test_dsh_fixture_tools.py`, and `test_agent_fixture_tools.py`. Passive-server cases are in `tests/unit/passive_server/test_dsh_headless.py`, `test_headless_service.py`, and `test_app_contracts.py`. Accounting cases are in `tests/unit/agents/realm_controller/test_dsh_usage_adapter.py` and `test_usage_extraction.py`.

Native cases are in `tests/integration/agents/dsh/test_native_companion.py`, `test_managed_acp.py`, `test_gateway_passive.py`, `test_fixture_acp.py`, `test_usage_intervals.py`, and `test_native_capabilities.py`. Real-provider qualification uses `scripts/qualification/dsh/qualify.py` and the maintained fixture helper; a passing controlled-native case does not become a real-provider result.

## Scenario Map

### agent-gateway

| Requirement | Scenario | Evidence Layer | Status |
| --- | --- | --- | --- |
| DSH ACP Agents Support Managed Gateway Operations | Gateway Attaches Between DSH Turns | Managed | Native pass: `test_native_dsh_gateway_continues_exact_session_and_keeps_debug_frames`; hermetic `test_attach_gateway_supports_runtime_owned_headless_backend`. |
| DSH ACP Agents Support Managed Gateway Operations | DSH Work Is Already Active | Managed | Native lock refusal in `test_native_dsh_gateway_continues_exact_session_and_keeps_debug_frames`; `test_plugin_busy_request_is_immediate_and_is_not_queued` (`tool=dsh`) proves no queue row. |
| DSH Immediate Dispatch Is Fenced at Native Handoff | The Driver Starts but DSH Rejects the Prompt | Managed | Hermetic pass: `test_worker_failure_before_admission_never_confirms_helper_launch` and `test_plugin_failed_attempt_never_dispatches_after_recovery` (`tool=dsh`, `failure=launch`). |
| DSH Immediate Dispatch Is Fenced at Native Handoff | The Managed Generation Changes Before Input | Managed | Hermetic pass: `test_plugin_failed_attempt_never_dispatches_after_recovery` (`tool=dsh`, `failure=replacement`) and `test_stale_native_receipt_cannot_confirm_new_attempt`. |
| DSH Immediate Dispatch Is Fenced at Native Handoff | Provider Failure Follows Native Admission | Managed | Hermetic pass: `test_plugin_failed_attempt_never_dispatches_after_recovery` (`tool=dsh`, `failure=after_handoff`) and `test_abrupt_native_death_retains_identity_without_replaying_input`. |
| DSH Mail and Plugin Integrations Reuse Core Admission | An Eligible Mail Reminder Wakes a DSH Agent | Managed | Native pass: `test_native_dsh_mailbox_reminders_repeat_without_changing_mail_transport` verifies repeated unchanged-inbox wakeups and the original offline binding. |
| DSH Mail and Plugin Integrations Reuse Core Admission | A Plugin Calls the DSH Agent Through Its Owner | Managed | Native pass: `test_cccc_owner_bound_offer_reaches_the_same_native_dsh_agent` verifies actual CCCC plugin dispatch, owner/runtime identity, and one no-buffer delivery. |

### agent-usage-records

| Requirement | Scenario | Evidence Layer | Status |
| --- | --- | --- | --- |
| DSH Consumption Uses Qualified Native Journal Evidence | ACP Reports Occupancy Without Consumption | Accounting | Hermetic pass: `test_context_occupancy_never_becomes_consumption`. |
| DSH Consumption Uses Qualified Native Journal Evidence | Native Journal Encoding Is Unsupported | Accounting | Hermetic pass: `test_newer_or_compressed_generation_never_falls_back`. |
| DSH Request Attempts Contribute Once | A Step Retries a Billed Request | Accounting | Hermetic pass: `test_failed_attempt_and_billed_retry_have_distinct_request_identities`. |
| DSH Request Attempts Contribute Once | A Settled Message Repeats an Attempt Sample | Accounting | Hermetic pass: `test_final_settlement_overrides_embedded_sample_and_charges_once`. |
| DSH Request Attempts Contribute Once | Interrupted Work Has No Reported Usage | Accounting | Hermetic pass: `test_missing_settlement_usage_stays_unknown_on_native_interruption`. |
| DSH Token Normalization Preserves Disjoint Buckets | DSH Reports All Disjoint Input Buckets | Accounting | Hermetic pass: `test_total_is_derived_only_from_all_disjoint_buckets`; actual controlled v4 rows are parsed by `test_real_controlled_rc3_capture_retains_two_resumed_native_turns`. |
| DSH Token Normalization Preserves Disjoint Buckets | A Cache Bucket Is Absent | Accounting | Hermetic pass: `test_missing_cache_bucket_keeps_aggregate_unavailable_and_zero_distinct`. |
| A DSH Managed Interval Can Cover Multiple Native Turns | A Child Result Starts Another Root Turn | Accounting + Native | Native pass: `test_native_child_result_starts_a_second_root_turn_and_is_accounted_once`, both spawn and fork; root 48 tokens, separate child 16, inherited fork samples excluded. |
| A DSH Managed Interval Can Cover Multiple Native Turns | The Same Interval Is Recovered Twice | Accounting | Hermetic pass: `test_managed_interval_counts_only_proven_roots_and_finalizes_once`, `test_concurrent_reconciliation_retains_original_generation_and_cutoff`, and `test_recording_outage_recovers_the_original_cached_finalization`. |
| DSH Resume Establishes Nonchargeable Historical Boundaries | Resume Reads Earlier Completed Turns | Accounting | Hermetic pass: `test_resume_boundary_excludes_all_previous_completed_roots` and `test_seeded_source_uses_last_tagged_cut_not_an_ancestor_marker`; native fork/resume interval test also excludes inherited requests. |
| DSH Resume Establishes Nonchargeable Historical Boundaries | Collection Stops Before Its Checkpoint Commits | Accounting | Hermetic pass: `test_checkpoint_failure_reprocesses_native_attempts_without_duplicates`. |

The sanitized `tests/fixtures/agent-usage-records/dsh-0.2.2-rc.3-controlled.json` records actual native rc.3 journal rows from two ACP prompts resumed across separate processes against the controlled Messages model. Each turn reports 11 uncached input, 5 output, zero cache reads/writes, and 16 total tokens. Native spawn/fork descendant evidence comes from `test_usage_intervals.py`, separately from that capture. Neither source claims paid-provider qualification. The [usage reference](usage-records.md#dsh-journal-accounting) defines source selection, attempt folding, interval correlation, and recovery.

### brain-launch-runtime

| Requirement | Scenario | Evidence Layer | Status |
| --- | --- | --- | --- |
| DSH Headless Selection Resolves to Its ACP Backend | Project Launch Selects DSH Headless | Managed | Hermetic maintained-path pass: the headless parameter of `test_dsh_project_profile_prepares_the_selected_managed_native_surface`; native manager fixture pass: `test_native_fixture_exact_resume` (`surface=manager`). |
| DSH Headless Selection Resolves to Its ACP Backend | Stale Controller Inspects a Completed Native Turn | Managed | Hermetic pass: `test_gateway_controls_preserve_newer_native_conversation` (`tool=dsh`, ensure/attach/detach/status). |
| DSH Runtime Configuration Is Explicit and Isolated | Two Agents Use Different Model Routes | Managed | Hermetic pass: `test_dsh_brains_preserve_explicit_selection_and_isolate_homes` and `test_selected_route_credentials_are_private_and_isolated`; both adapter routes have separate native fixture cases. |
| DSH Runtime Configuration Is Explicit and Isolated | A Chat Endpoint Is Supplied to a Messages Route | Managed | Hermetic pass: `test_protocol_mismatch_fails_before_projection`; `test_all_dsh_surfaces_prepare_the_same_explicit_route` checks each declared protocol. |
| DSH Runtime Configuration Is Explicit and Isolated | The Provider Route Is Missing | Managed | Hermetic pass: `test_dsh_missing_route_and_undeclared_model_fail_before_launch`, `test_missing_reference_fails_before_creating_home`, and `test_explicit_model_metadata_is_required`. |
| DSH Roles Are Applied as Literal Native System Instructions | Role Contains Template-Like Text | Managed | Native pass: `test_native_module_literal_prompt_and_exact_resume`, both adapters; literal role text remains in native system instructions alongside built-in guidance/tools. |
| DSH Roles Are Applied as Literal Native System Instructions | An Empty Role Replaces an Earlier Role | Managed | Hermetic pass: `test_empty_role_and_credentials_replace_stale_managed_content` and `test_empty_role_registers_no_stale_section`. |
| DSH Headless Lifecycle Uses the Managed Turn Envelope | A Headless Turn Exits Between Prompts | Managed | Native pass: `test_managed_tmux_exact_resume_and_usage_finalization` and `test_native_dsh_gateway_continues_exact_session_and_keeps_debug_frames`. |
| DSH Headless Lifecycle Uses the Managed Turn Envelope | An Operator Resets the Native Conversation | Managed | Native pass: `test_managed_tmux_exact_resume_and_usage_finalization` now includes explicit `mode=new`, a distinct native ID, excluded old prompt history, and retained earlier usage; hermetic `test_gateway_service_explicit_new_headless_prompt_uses_new_session_selection`. |
| DSH Headless Lifecycle Uses the Managed Turn Envelope | An Attempt Dies After Admission | Managed | Hermetic pass: `test_abrupt_native_death_retains_identity_without_replaying_input` (admission/claim) and `test_plugin_failed_attempt_never_dispatches_after_recovery` (`tool=dsh`). |

### dsh-headless-control

| Requirement | Scenario | Evidence Layer | Status |
| --- | --- | --- | --- |
| DSH Headless Control Uses a Qualified ACP Connection | Required Resume Capability Is Missing | Transport + Native | Hermetic pass: `test_resume_capability_is_required_only_for_continuation`; native conformance separately verifies the pinned executable advertises resume. |
| DSH Headless Control Uses a Qualified ACP Connection | Provider Emits Invalid Protocol Output | Transport + Native | Hermetic pass: `test_invalid_stdout_fails_every_pending_request` and `test_eof_is_failure_and_raw_frames_remain_distinct`. |
| DSH Continuation Selects an Exact Native Session | A Later Process Continues the Conversation | Transport + Native | Native pass: `test_native_module_literal_prompt_and_exact_resume`, `test_managed_tmux_exact_resume_and_usage_finalization`, and `test_native_fixture_exact_resume`. |
| DSH Continuation Selects an Exact Native Session | Saved Session Cannot Be Resumed | Transport + Native | Hermetic pass: `test_missing_resume_does_not_create_replacement_or_claim_handoff` and `test_wrong_workspace_refuses_before_any_tmux_or_native_activation`. |
| ACP Updates and Client Requests Remain Serviceable During a Prompt | Permission Arrives Before Completion | Transport + Native | Hermetic pass: `test_reader_handles_permission_notifications_and_reversed_responses` and `test_permission_handler_denies_unanswered_questions_and_checks_binding`. |
| ACP Updates and Client Requests Remain Serviceable During a Prompt | An Update Belongs to Another Session | Transport + Native | Hermetic pass: `test_two_workers_preserve_exact_session_and_separate_raw_frames` retains unrelated raw frames while excluding them from bound semantic output. |
| Prompt Dispatch and Completion Have Distinct Evidence | Driver Starts Before Native Admission | Transport + Native | Hermetic pass: `test_worker_failure_before_admission_never_confirms_helper_launch` and `test_plugin_dispatch_waits_for_handoff_but_not_completed_turn` (`tool=dsh`). |
| Prompt Dispatch and Completion Have Distinct Evidence | Provider Stops at an Output Limit | Transport + Native | Hermetic pass: `test_native_incomplete_reason_is_preserved` (`max_tokens`, `refusal`, `cancelled`). |
| DSH Interruption Uses Native Cancellation Before Forced Exit | Native Cancellation Settles | Transport + Native | Hermetic pass: `test_explicit_interrupt_sends_native_cancel_and_waits_for_settlement` and `test_native_cancelled_bridge_outcome_is_interrupted_without_operator_flag`; controlled-native `test_independent_controller_interrupts_the_bound_native_attempt` and the real DeepSeek manager qualification also pass. |
| DSH Interruption Uses Native Cancellation Before Forced Exit | Native Cancellation Stalls | Transport + Native | Hermetic pass: `test_hung_native_cancellation_preserves_failure_and_reaps_the_worker`, `test_replaced_leader_birth_never_authorizes_group_signals`, and `test_external_native_cleanup_requires_both_birth_and_group_ownership`. |
| Turn Closure Preserves Native Persistence and Process Ownership | Prompt Completes Before Persistence Flush Fails | Transport + Native | Hermetic pass: `test_flush_failure_retains_observed_native_outcome` preserves native settlement separately from failed cleanup. |
| Turn Closure Preserves Native Persistence and Process Ownership | Controller Times Out During Active Execution | Transport + Native | Hermetic pass: `test_controller_timeout_requires_terminal_proof_before_usage_finalization` and `test_runner_timeout_keeps_original_owned_identity_without_cancelling_handoff`. |
| DSH Operation Support Is Explicit | Caller Requests Unsupported Session Fork | Transport + Native | Native pass: `test_native_acp_fork_request_is_unsupported_without_another_conversation` verifies JSON-RPC method-not-found, unchanged session listing, and zero model requests; published capability test also lists fork unsupported. |
| DSH Operation Support Is Explicit | Profile Files Change During a Turn | Transport + Native | Native pass: `test_native_profile_edits_during_a_turn_remain_startup_only` edits the loaded profile/role at an active pre-step and verifies the original configuration in the same process; published capabilities continue to declare startup-only activation. |

### native-cli-provider-support

| Requirement | Scenario | Evidence Layer | Status |
| --- | --- | --- | --- |
| Maintained native CLI provider set excludes Gemini CLI | Current provider selection rejects Gemini | Managed | Hermetic pass: `test_removed_provider_identifiers_stay_rejected_on_maintained_surfaces` rejects `gemini`, `gemini_cli`, and `gemini_headless` through real project CLI, backend selection, and launch metadata parsing. |
| Maintained native CLI provider set excludes Gemini CLI | Remaining provider set stays available | Managed | Full existing Claude/Codex/Kimi unit regressions pass; `test_case_resolution_has_no_model_or_account_defaults` and `test_managed_preparation_uses_real_project_credential_projection` cover their maintained preparation. |
| Maintained native CLI provider set excludes Gemini CLI | DSH Is Selected Through Maintained Tool Surfaces | Managed | Hermetic pass: `test_dsh_native_tools_and_recipe_selection_are_maintained`, `test_dsh_credential_commands_are_api_only`, `test_dsh_project_profile_prepares_the_selected_managed_native_surface` (headless parameter), and `test_dsh_launch_persists_supported_authority`. |

### passive-server-headless-management

| Requirement | Scenario | Evidence Layer | Status |
| --- | --- | --- | --- |
| Passive server can launch native headless agents | Successful headless launch | Managed | Hermetic pass: `TestHeadlessLaunch.test_launch_publishes_shared_registry_record` verifies managed launch metadata, shared registry publication, and saved authority. |
| Passive server can launch native headless agents | Invalid working directory returns 422 | Managed | Hermetic HTTP pass: `TestHeadlessLaunchEndpoint.test_missing_working_directory_returns_422`. |
| Passive server can launch native headless agents | Unsupported backend returns 422 | Managed | Hermetic pass: `test_unsupported_headless_backend_returns_422_before_runtime_start` rejects incompatible backend resolution with no provider start or saved authority. |
| Passive server can launch native headless agents | Successful Kimi headless launch | Managed | Hermetic pass: `test_kimi_launch_preserves_authority_and_accepts_managed_follow_up` verifies `kimi_headless` authority and a later accepted managed turn. |
| Passive server can launch native headless agents | Successful DSH ACP Launch | Managed | Hermetic pass: `test_dsh_launch_persists_supported_authority` and `test_dsh_passive_birth_uses_the_prepared_brain_and_selected_route`; native gateway/passive continuation also passes. |
| Passive Server Preserves DSH Headless Execution Evidence | DSH Events and Raw Output Are Queried | Managed | Native pass: `test_native_dsh_gateway_continues_exact_session_and_keeps_debug_frames`; hermetic `test_dsh_restart_reconciles_original_attempt_without_prompt_replay` verifies distinct canonical/raw routes. |
| Passive Server Preserves DSH Headless Execution Evidence | Passive Server Restarts After Native Admission | Managed | Hermetic pass: `test_dsh_restart_reconciles_original_attempt_without_prompt_replay` (live/dead host); native integration reconstructs terminal authority, reads events/raw/usage, and continues only on a new explicit prompt. |

### test-agent-launch-fixtures

The following preparation and controlled-native checks passed. The real DeepSeek Messages manager lane also passes with the explicitly selected `.env` references and qualified model metadata. Real self-hosted qualification remains `not_run` because no compatible deployment/model was selected. An earlier qualification-runner invocation without `--env-file` exited 2 and correctly refused ambient authentication.

| Requirement | Scenario | Evidence Layer | Status |
| --- | --- | --- | --- |
| Client protocols are selected explicitly | Chat-only server cannot satisfy Codex preparation | Managed + Live | Hermetic pass: `test_chat_only_descriptor_cannot_satisfy_codex`. |
| Client protocols are selected explicitly | DeepSeek endpoints map to the selected client | Managed + Live | Hermetic pass: `test_case_resolution_has_no_model_or_account_defaults`, `test_protocol_paths_are_preserved_or_rejected_explicitly`, and `test_dsh_messages_preserves_an_explicit_version_path`. |
| Client protocols are selected explicitly | DSH Uses Its Selected Adapter Protocol | Managed + Live | Hermetic pass: `test_all_dsh_surfaces_prepare_the_same_explicit_route`; native `test_native_fixture_exact_resume` passes cloud Messages and generic self-hosted Chat configurations. |
| Fixture qualification records actual evidence and limitations | Self-hosted endpoint is not configured | Managed + Live | Hermetic pass: `test_live_runner_needs_explicit_external_credentials`; an actual runner invocation without `--env-file` exited 2 and reported the unconfigured self-hosted lane as `not_run`. No real self-hosted prerequisite has been selected. |
| Fixture qualification records actual evidence and limitations | Historical capture records Qwen usage | Managed + Live | Hermetic pass: `test_real_two_turn_capture_assembles_native_requests_without_replay` reparses retained Claude/Codex/Kimi Qwen fixtures; their factual upstream-model metadata remains unchanged and current helpers use maintained entrypoints. |
| Fixture qualification records actual evidence and limitations | DSH Headless Qualification Does Not Imply Interactive Support | Managed + Live | `test_live_runner_needs_explicit_external_credentials` checks the headless runner's separate scope. Web preparation is now covered by `test_web_preparation_reuses_explicit_cases_and_operator_posture`, with its own [Web acceptance map](dsh-web-acceptance.md); the accepted ACP result remains specific to headless control. |
| DSH Headless Fixtures Reuse Generic Local Configuration | Fresh Host Uses DeepSeek Without a Local Model | Managed + Live | Hermetic pass: `test_dsh_cli_resolves_without_saved_native_login`; controlled and real DeepSeek manager qualification pass without a self-hosted deployment or vendor-login JSON. |
| DSH Headless Fixtures Reuse Generic Local Configuration | Generic Self-Hosted Route Has No Explicit Capabilities | Managed + Live | Hermetic pass: `test_dsh_refuses_missing_capacities_before_allocating_state` and `test_explicit_model_metadata_is_required`. |
| DSH Headless Fixtures Reuse Generic Local Configuration | CI Has No Local Provider Account | Managed + Live | Hermetic and controlled-native passes use synthetic credentials; `test_dsh_uses_only_the_selected_env_file` and `test_live_runner_needs_explicit_external_credentials` block ambient auth fallback. |

## Executed Checks and Remaining Gates

The full unit run on 2026-11-16 passed **4,018 tests with 14 skips** behind an explicit private tmux socket. The targeted lifecycle/connection/driver run passed **41 tests**, including abrupt native death at admission and claim. Gemini rejection, passive inherited-scenario, and bridge-cancellation regressions also passed in targeted runs. After the resumed-controller cancellation repair, the final native integration run passed **17 tests in 98.46 seconds**. These cover unsupported fork, startup-only configuration, exact continuation, explicit reset, independent-controller interruption/stop, gateway/passive control, raw/manager fixtures, and spawned/forked descendant accounting. The map identifies which scenarios use hermetic peers, actual native processes, or both.

Format, lint, strict type checking, strict documentation build, distribution build, Twine metadata checks, and strict validation of both OpenSpec changes passed during this acceptance work. Distribution inventory checks verified packaged DSH resources while excluding development tooling, reference checkouts, credential bundles, and private run state. Ignored audit reports live under `tmp/dsh/acceptance/`. Final acceptance must use the validation results for the final reviewed source tree.

A final per-prompt reasoning correction uses the common mapping's canonical preset key. Requested levels above the declared ladder saturate correctly, and explicit off remains valid for models without reasoning. The subsequent launch/lifecycle/gateway regression run passed **54 tests**, including four direct-invocation and native-profile preparation cases. Global formatting, lint, and strict type checking also passed after this correction.

### Live Qualification

The operator selected the checkout's ignored `.env` as the credential source. Only its required DeepSeek references were copied into an owner-only external credential file. Authenticated model discovery reported `deepseek-flash` with a 1,048,576-token context and 393,216-token output capacity. Qualification selected the Messages route and a 4,096-token request output cap with reasoning off.

An initial run exposed missing active-process restoration in an independently reconstructed controller. The repair validates the persisted attempt, runtime, generation, workspace, native process birth, and driver process birth before interruption or stopping. Invalid authority fails closed. Its focused regression suite passes 67 cases, and five controlled-native interruption/stop/gateway cases pass. Original failed-run outcomes remain intact; qualification uses a fresh explicit run rather than resending a failed delivery.

The fresh real-provider run passed all five required checks: native shell-tool completion, exact native continuation across workers, public journal consumption after two completed submissions, interruption from an independent manager controller, and two isolated homes/native sessions. It used `deepseek-flash` through `anthropic_messages` on the manager surface with DSH `0.2.2-rc.3`. Executable SHA-256 was `36f86742e0c3cc1c3b2dbaa6582ee00b0c37bc4f5a190f7531b5303bf3efb6d9`; package-code SHA-256 was `ac0a9f14c56acd12081b12702887fccc5948a07e0a9c9f27128e0d5eff6a088c`. Matching npm/source versions remain qualified behavior evidence rather than source-commit attestation. Private credentials, transcripts, endpoint values, and run receipts remain outside the checkout.

Real self-hosted qualification requires an explicitly configured compatible model other than Qwen3.8. That lane remains `not_run` with its missing-prerequisite reason. Interactive Web qualification belongs to the successor change and is not established by this headless result.

## Ordered Roadmap

1. Headless implementation and acceptance are complete in `openspec/changes/archive/2026-11-17-dsh-01-add-acp-headless-backend/`, including real-provider evidence and final regression checks. Synchronize its validated delta specs before starting the successor.
2. Apply `openspec/changes/archive/2026-11-17-dsh-02-add-interactive-web-backend/` using the same qualified source/build, isolated configuration, literal prompt companion, native journal reader, and ledger. Interactive Web ownership, browser/API coexistence, admission races, and human-origin accounting require their own implementation and acceptance.

Keep the combined issue [#74](https://github.com/igamenovoer/houmao/issues/74) scope open until both ordered changes have accepted evidence. A complete headless implementation does not qualify the Web surface. Final headless acceptance includes the regression checks for the reviewed source tree before synchronizing the first change's delta specs.
