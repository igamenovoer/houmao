# DSH Web Acceptance Map

This map covers all 96 delta scenarios in `dsh-02-add-interactive-web-backend`. Each row points to executed hermetic or controlled-native evidence. Web also has its own real DeepSeek browser/API smoke, separate from the accepted [headless predecessor](dsh-headless-acceptance.md). Real self-hosted qualification remains `not_run` because no compatible deployment/model was selected.

## Executed Evidence and Limits

The final combined native suite passed 84 cases in 297.72 seconds: 17 predecessor regressions and 67 Web/qualification cases. It includes the seven actual native browser cases, both generic protocols on raw/manager surfaces, outer manager exact relaunch with fresh execution identities, and immutable accounting. An earlier focused browser run passed seven cases in 42.87 seconds; the complete outer manager fixture matrix passed two cases in 27.11 seconds. Chromium 156.0.8078.4 ran headlessly through Bun and the installed Playwright API.

Native lifecycle tests cover two owned hosts, external-host refusal without mutation, missing-companion/port-conflict rollback, exact relaunch, stale-controller fences, and cleanup after hard supervisor death. Gateway checks exercise actual HTTP state/history, owner-bound CCCC, recurring mail reminders, and terminal outcomes distinct from admission. Accounting covers mixed input, separate human work, actual route changes, lost receipts, journal replay, and relaunch boundaries. The final unit gate passed 4,150 tests with 14 skipped in 91.20 seconds; format reported 955 files unchanged, Ruff lint passed, and strict mypy passed all 470 source files.

The selected real DeepSeek manager Web smoke passed all seven checks: API shell-tool completion, browser shell-tool completion, exact continuation, completed human-origin usage, human-turn interruption, exact host relaunch, and two isolated homes. It used `deepseek-flash`, `anthropic_messages`, unattended posture, native protocol 1, and Chromium 156.0.8078.4. Cleanup passed and the report recorded no extra limits. The explicitly selected credential snapshot and paid evidence remain outside the checkout and were not copied into this map. A separate no-env invocation returned `not_run` and exit 2, refusing ambient authentication.

Build inspection reconfirmed source `39163dd30f703a79079e2d2446545cff3c453738`, executable `0.2.2-rc.3`, executable SHA-256 `36f86742e0c3cc1c3b2dbaa6582ee00b0c37bc4f5a190f7531b5303bf3efb6d9`, and package-code SHA-256 `ac0a9f14c56acd12081b12702887fccc5948a07e0a9c9f27128e0d5eff6a088c`. Published package metadata does not attest a source commit. The [compatibility reference](dsh-web.md), [native control contract](dsh-web-control.md), and [integration reference](dsh-web-integrations.md) define the qualified boundaries.

## Evidence Index

Native functions resolve in `tests/integration/agents/dsh/web/`: `test_native_control.py`, `test_dispatch_permission.py`, `test_browser_coexistence.py`, `test_fixture_web.py`, `test_managed_lifecycle.py`, `test_supervisor_process.py`, `test_gateway_native.py`, `test_gateway_projection.py`, and `test_usage.py`. The current headless fixture continuation has its own suite at `tests/integration/agents/dsh/test_fixture_headless.py`.

Hermetic Web functions resolve under `tests/unit/agents/realm_controller/` in `test_dsh_web_models.py`, `test_dsh_web_backend.py`, `test_dsh_web_client.py`, `test_dsh_web_companion.py`, `test_dsh_web_observation.py`, `test_dsh_web_gateway.py`, and `test_dsh_web_usage.py`. Other Web cases are in `tests/unit/passive_server/test_dsh_web_observation.py`, `tests/unit/srv_ctrl/test_dsh_web_inspection.py`, `tests/unit/agents/test_dsh_launch_surfaces.py`, `tests/unit/agents/test_dsh_fixture_tools.py`, and `tests/unit/agents/test_dsh_web_fixture_tools.py`. Unchanged terminal/headless cases resolve in `tests/unit/agents/realm_controller/test_gateway_support.py`, `test_gateway_manifest_preservation.py`, and `tests/unit/passive_server/test_observation.py` / `test_app_contracts.py`. The retained historical usage parser case is in `tests/unit/agents/realm_controller/test_usage_extraction.py`.

All tmux-backed checks clear `TMUX` and `TMUX_PANE`, force a private `-S` or `-L` target for every command, and clean up only their owned server. Reports contain no real keys, launch tokens, signed URLs, cookies, private transcripts, or credential-bearing live paths. Test-only DOM automation stays outside product code.

## Native Home Refresh Evidence

The follow-on change `add-native-agent-home-refresh` adds `tests/integration/agents/dsh/web/test_refresh.py` and `test_refresh_gateway.py`. The final combined suite passed all 28 cases in 68.12 seconds against the explicitly selected `0.2.2-rc.3` executable: 26 direct-native cases and two public runtime/gateway cases, including real two-agent CLI/direct-gateway/passive-server acceptance. Both public cases passed again in 11.08 seconds after the final captured-identity handoff guard. Direct native checks use no tmux; gateway cases use the existing fixture's cleared inherited selectors and explicit private socket. All refresh cases use synthetic credentials, no ambient authentication, and zero refresh-created model requests. Ordinary browser and skill-history cases create their own explicitly controlled model turns.

The independent contract/authority suite passed 53 cases: 27 regressions for strict evidence, owner identity/time, native readiness and qualified automatic coverage, plus 26 native-home authority cases. The final focused model/deadline/client/backend/companion suite passed 85 cases, including expiry during authentication and client-lock acquisition, deadline forwarding, and replacement during authentication. Focused strict typing passed both modified Python backend modules and the native refresh service. Fixture audit found only source fixtures in the checkout, no credential or runtime-state artifacts. Native credentials and logs remain in disposable external test roots.

| Boundary | Executed Evidence |
| --- | --- |
| Skill add/update/remove, same identity/journal, verified no-op | `test_native_common_refresh_updates_skill_catalog_and_then_noops` |
| Native extension skill assets require source/runtime comparison | `test_native_office_provider_cache_is_compared_with_current_assets` |
| Opaque cached providers cannot claim complete current, including empty providers | Both cases of `test_opaque_native_provider_cannot_establish_complete_current_scope` |
| MCP declaration replacement, negotiated tool generations, unknown implementation revision | `test_native_mcp_declarations_and_connection_generations` |
| Applied declaration freshness remains separate from unavailable MCP health | `test_applied_unreachable_mcp_keeps_declaration_freshness_separate_from_health` |
| Actual loaded skill history remains intact while later native loads read edited bodies | `test_loaded_skill_history_survives_refresh_and_next_load_reads_new_body` |
| Autonomous update without Houmao receipt | `test_native_watcher_update_needs_no_houmao_receipt` |
| Native watcher remains active during managed reconciliation | `test_native_watcher_can_race_managed_reconciliation` |
| Two native homes remain isolated | `test_native_refresh_keeps_distinct_homes_isolated` |
| Passive reads leave cache/configuration unchanged | `test_native_read_does_not_apply_edited_profile` |
| Busy maintenance and host-shared native child refuse immediately | `test_native_refresh_refuses_existing_maintenance_without_waiting`, `test_refresh_refuses_host_shared_native_child` |
| Competing native Agent activation cannot start during shared refresh | `test_native_child_activation_cannot_race_shared_refresh` |
| Browser-native work wins between observation and managed refresh admission | `test_browser_turn_wins_before_native_refresh_admission` |
| Missing confirmation retains native work and responsive observation | `test_timed_out_refresh_remains_observable_and_settles_without_replay` |
| Actual wire response loss retains original native work without replay | `test_actual_native_http_response_loss_does_not_replay_refresh` |
| Native preflight cannot reset an expired operation deadline | `test_native_observation_cannot_reset_expired_refresh_deadline` |
| Late settlement cannot start a later resource restart after expiry | `test_expired_native_apply_does_not_start_later_resource_restarts` |
| Busy native serialization leaves no deferred mutation | `test_busy_native_serializer_leaves_no_deferred_mutation` |
| Invalid readiness prevents native finally from waking queued input | `test_invalid_readiness_retains_maintenance_until_explicit_disposal` |
| Invalid input is not repaired from a launch manifest | `test_invalid_native_input_reports_failure_without_repair` |
| Broader native pending/failure preserves actual common effects | Both cases of `test_broader_native_result_preserves_confirmed_common_state` |
| Real native Loader activation failure retains applied common effects | `test_failed_native_replacement_retains_applied_common_effects` |
| Lifecycle configuration cannot replace the running agent through refresh | `test_refresh_rejects_lifecycle_profile_changes_before_apply` |
| Public native-home and refresh routes map actual native pending/current/no-op/MCP evidence | `test_public_gateway_native_refresh_preserves_real_common_evidence` in `test_refresh_gateway.py` |
| Home authority requires the captured live primary surface and exact session bindings | `test_native_refresh_authority.py`: caller/native home separation, headless between-worker envelope, stale/missing/dead/reused identity, explicit native identity allowlist, and private home material left unread |
| Two native agents share scoped CLI, direct gateway and passive refresh semantics | `test_two_native_agents_share_cli_gateway_and_passive_refresh_contract` in `test_refresh_gateway.py`; real loopback HTTP, native watcher/no-op, broader partial failure, isolated inventories and unchanged identities |

The native-result probe supplies controlled pending/failure diagnostics around actual native profile reconciliation. These checks establish result preservation, not arbitrary HMR code replacement. Full HMR replacement, arbitrary user extension lifecycle behavior, and external MCP package revisions remain outside the executed claims. The [control contract](dsh-web-control.md#common-plugin-observation-and-refresh) records these limits.

## Versioned Skill Mount Evidence

The versioned mount qualifies DSH `0.2.2-rc.3` under the `standard` native preset. The four cases in `tests/integration/agents/dsh/web/test_skill_file_edits.py` exercise the native user-facing skill catalog, the model-facing `skill` and `read` tools, and owner opt-in through the managed backend. They verify revision-specific bodies and assets, collision and unsafe-path refusal, settlement of exclusive native maintenance, same-home relaunch, and add, update, and removal without changing the native process or conversation. An active synthetic MCP server stays connected while its replacement declaration remains pending. The controlled model receives requests only from the explicitly prompted turns.

The cross-account case in `tests/integration/agents/dsh/web/test_gateway_file_edits.py` ran with a provisioned second Linux account and separate isolated tmux sockets. The source had a configured SSH signer and no attached gateway or read access to the target's files. Its signed manager commands created two candidates. The owner separately authorized publication after the target's busy turn, and the target loaded the peer's skill and asset through its native tools. The test also checks the stale candidate, replaced generation, revoked credential, and absent target listener.

## Scenario Map

### agent-gateway

| Requirement | Scenario | Evidence Layer | Evidence and Limits |
| --- | --- | --- | --- |
| Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state | Managed-agent crash changes upstream status without corrupting gateway health | Existing terminal regression | `test_gateway_status_invalidates_stale_live_bindings`. |
| Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state | Replacement upstream instance increments the managed-agent epoch | Existing terminal regression | `test_gateway_status_invalidates_stale_live_bindings`. |
| Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state | Manual modal interaction changes surface eligibility without corrupting gateway health | Existing terminal regression | `test_gateway_hook_posture_admission_matrix_and_decision_records`; `test_gateway_degraded_hook_channel_preserves_tui_only_refusal`. |
| Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state | Foreground gateway status exposes the tmux execution handle | Existing terminal regression | `test_gateway_service_exposes_foreground_tmux_execution_metadata`. |
| Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state | Uncertain surface classification stays explicit | Existing terminal regression | `test_gateway_status_invalidates_stale_live_bindings`. |
| Gateway status separates gateway health, upstream-agent state, recovery, admission, surface eligibility, and execution state | Web Readiness Does Not Depend on a Terminal Parser | Hermetic + Native | `test_web_plugin_event_confirms_native_ready_only_handoff_without_terminal_tracking`. |
| Gateway direct prompt control uses explicit admission policies | Default policy sends to a stable ready TUI with no pending input | Existing terminal regression | `test_gateway_prompt_admission_policy_matrix_and_structural_checks`. |
| Gateway direct prompt control uses explicit admission policies | Ready-only backs off while the TUI is busy | Existing terminal regression | `test_gateway_prompt_admission_policy_matrix_and_structural_checks`. |
| Gateway direct prompt control uses explicit admission policies | Ready-only backs off when hooks report an active or blocked turn | Existing terminal regression | `test_gateway_hook_posture_admission_matrix_and_decision_records`; `test_gateway_degraded_hook_channel_preserves_tui_only_refusal`. |
| Gateway direct prompt control uses explicit admission policies | If-no-pending submits while busy when the queue is visibly empty | Existing terminal regression | `test_gateway_prompt_admission_policy_matrix_and_structural_checks`. |
| Gateway direct prompt control uses explicit admission policies | If-no-pending backs off from an existing provider-native queue | Existing terminal regression | `test_gateway_prompt_admission_policy_matrix_and_structural_checks`. |
| Gateway direct prompt control uses explicit admission policies | If-no-pending backs off while hooks report blocked | Existing terminal regression | `test_gateway_hook_posture_admission_matrix_and_decision_records`; `test_gateway_degraded_hook_channel_preserves_tui_only_refusal`. |
| Gateway direct prompt control uses explicit admission policies | Degraded hook channel adds no refusal reasons | Existing terminal regression | `test_gateway_hook_posture_admission_matrix_and_decision_records`; `test_gateway_degraded_hook_channel_preserves_tui_only_refusal`. |
| Gateway direct prompt control uses explicit admission policies | If-no-pending treats uncertainty conservatively | Existing terminal regression | `test_gateway_prompt_admission_policy_matrix_and_structural_checks`. |
| Gateway direct prompt control uses explicit admission policies | Always submits despite visible pending input | Existing terminal regression | `test_gateway_prompt_admission_policy_matrix_and_structural_checks`. |
| Gateway direct prompt control uses explicit admission policies | Closely spaced conditional submissions may both dispatch before repaint | Existing terminal regression | `test_gateway_if_no_pending_is_observational_across_provider_repaint`. |
| Gateway direct prompt control uses explicit admission policies | Later conditional submission reacts to observed pending state | Existing terminal regression | `test_gateway_if_no_pending_is_observational_across_provider_repaint`. |
| Gateway direct prompt control uses explicit admission policies | Admission decision records carry hook facts | Existing terminal regression | `test_gateway_hook_posture_admission_matrix_and_decision_records`; `test_gateway_degraded_hook_channel_preserves_tui_only_refusal`. |
| Gateway direct prompt control uses explicit admission policies | Non-default policy is rejected for headless prompt control | Existing terminal regression | `test_gateway_rejects_nondefault_policy_for_native_headless`. |
| Gateway direct prompt control uses explicit admission policies | TUI new-session workflow requires ready-only policy | Existing terminal regression | `test_gateway_rejects_nondefault_policy_for_tui_new_session`. |
| Gateway direct prompt control uses explicit admission policies | Web Ready-Only Rechecks After Human Input | Hermetic + Native | `test_browser_wins_after_api_readiness_before_native_handoff`; `test_native_permission_is_rechecked_after_async_preparation_without_insertion_or_replay`. |
| Gateway direct prompt control uses explicit admission policies | Web If-No-Pending Explicitly Admits Busy Input | Hermetic + Native | `test_native_operator_queue_and_abandonment_are_attempt_scoped`; `test_web_explicit_operator_policy_is_forwarded_only_when_requested`. |
| Gateway direct prompt control uses explicit admission policies | Web Always Preserves Structural Refusals | Hermetic + Native | `test_native_guarded_refusals_do_not_insert`; `test_native_protocol_owner_and_session_guards_precede_mutation`. |
| DSH Web Ordinary Events Use Native Immediate Admission | Browser Input Wins the Admission Race | Hermetic + Native | `test_browser_wins_after_api_readiness_before_native_handoff`; `test_owned_web_gateway_plugin_and_public_requests_share_native_state_without_replay_queue`. |
| DSH Web Ordinary Events Use Native Immediate Admission | Provider Replacement Follows Native Admission | Hermetic + Native | `test_web_ordinary_event_native_refusal_or_execution_loss_never_replays`; `test_native_permission_is_rechecked_after_async_preparation_without_insertion_or_replay`. |
| Web Gateway Observation Uses Structured Native State | Browser Approval Blocks Native Work | Hermetic + Native | `test_as_is_browser_answers_question_while_api_only_observes`; `test_web_ordinary_event_refuses_closed_native_admission_before_any_dispatch`. |
| Web Gateway Observation Uses Structured Native State | Terminal Tracking Is Requested for DSH Web | Hermetic + Native | `test_web_terminal_routes_explicitly_report_supported_native_inspection`; `test_manager_web_gateway_attach_rejects_terminal_timing_before_any_controller_effect`. |

### agent-usage-records

| Requirement | Scenario | Evidence Layer | Evidence and Limits |
| --- | --- | --- | --- |
| DSH Web Accounting Includes Verified Human-Initiated Work | A Human Completes a Browser Turn | Accounting + Native | `test_native_web_fixture_keeps_one_browser_api_session`; `test_native_web_managed_human_followup_and_relaunch_charge_exactly_once`. |
| DSH Web Accounting Includes Verified Human-Initiated Work | Human Changes the Model in the Browser | Accounting + Native | `test_browser_model_selection_controls_the_actual_human_request`; `test_native_web_actual_changed_model_is_retained_per_request`. |
| Mixed Web Input Does Not Create Duplicate or Invented Charges | Human Steering Shares a Managed Turn | Accounting + Native | `test_native_web_human_steering_shares_one_managed_charge`; `test_managed_mixed_and_distinct_human_turns_charge_once`. |
| Mixed Web Input Does Not Create Duplicate or Invented Charges | Human Follow-Up Runs Before a Programmatic Wait Returns | Accounting + Native | `test_native_web_managed_human_followup_and_relaunch_charge_exactly_once`; `test_unrelated_pending_managed_operation_does_not_absorb_human_work`; `test_manager_web_waits_for_exact_operation_usage`. |
| Web Observation Recovery Preserves Accounting Continuity | API Stream Repeats Events After Reconnect | Accounting + Native | `test_concurrent_reconciliation_preserves_generation_and_cutoff`; `test_native_web_managed_human_followup_and_relaunch_charge_exactly_once`; `test_native_web_lost_receipt_recovers_usage_without_resubmission`. |
| Web Observation Recovery Preserves Accounting Continuity | Host Relaunch Preserves a Conversation | Accounting + Native | `test_attachment_excludes_history_and_relaunch_preserves_original_rows`; `test_native_web_managed_human_followup_and_relaunch_charge_exactly_once`; `test_native_web_fixture_keeps_one_browser_api_session`. |

### brain-launch-runtime

| Requirement | Scenario | Evidence Layer | Evidence and Limits |
| --- | --- | --- | --- |
| DSH TUI Posture Resolves to a Web Backend | Developer Launches DSH Interactively | Hermetic + Native | `test_dsh_project_profile_prepares_the_selected_managed_native_surface`; `test_native_web_fixture_keeps_one_browser_api_session`. |
| DSH TUI Posture Resolves to a Web Backend | A DSH Headless Profile Is Launched | Hermetic + Native | `test_dsh_project_profile_prepares_the_selected_managed_native_surface`; `test_native_fixture_exact_resume`. |
| Native Human Surface Is Distinct From Process Supervision | A Web Host Is Supervised in Tmux | Hermetic + Native | `test_web_manifest_serializes_a_browser_surface_and_separate_log_supervision`; `test_supervisor_keeps_native_output_private_and_reaps_captured_descendants`. |
| Native Human Surface Is Distinct From Process Supervision | Native Surface Metadata Is Incompatible | Hermetic + Native | `test_web_manifest_rejects_missing_mismatched_or_terminal_authority`. |
| Managed DSH Web Startup Publishes Only Verified Authority | The Host Starts Without Its Managed Control Companion | Hermetic + Native | `test_missing_companion_rolls_back_only_the_created_supervisor`. |
| Managed DSH Web Startup Publishes Only Verified Authority | Two DSH Web Agents Share a Project | Hermetic + Native | `test_two_owned_hosts_reconnect_without_retargeting_or_disclosing_native_output`. |
| Web Human Interaction Follows the Selected Operator Policy | Human Operates an As-Is DSH Session | Hermetic + Native | `test_dsh_launch_plan_preserves_as_is_native_permissions`; `test_as_is_browser_answers_question_while_api_only_observes`. |
| Web Human Interaction Follows the Selected Operator Policy | Automated Web Qualification Has No Display | Hermetic + Native | `test_browser_api_alternation_navigation_and_independent_auth`; `test_web_preparation_reuses_explicit_cases_and_operator_posture`. |
| Web Relaunch Preserves Logical Identity and Changes Execution Identity | A Stale Controller Inspects a Relaunched Host | Hermetic + Native | `test_late_completed_controller_cannot_overwrite_an_explicit_native_reset`; `test_gateway_controls_preserve_newer_native_conversation`. |
| Web Relaunch Preserves Logical Identity and Changes Execution Identity | A Gateway Restarts While the Web Host Stays Live | Hermetic + Native | `test_two_owned_hosts_reconnect_without_retargeting_or_disclosing_native_output`; `test_owned_web_gateway_plugin_and_public_requests_share_native_state_without_replay_queue`. |

### dsh-web-control

| Requirement | Scenario | Evidence Layer | Evidence and Limits |
| --- | --- | --- | --- |
| DSH Web Control Requires Houmao Launch Ownership | Operator Tries to Adopt a Manually Started Host | Hermetic + Native | `test_external_supervisor_session_is_refused_without_changing_its_pane`. |
| DSH Web Control Requires Houmao Launch Ownership | Gateway Reattaches to an Existing Owned Host | Hermetic + Native | `test_two_owned_hosts_reconnect_without_retargeting_or_disclosing_native_output`; `test_owned_web_gateway_plugin_and_public_requests_share_native_state_without_replay_queue`. |
| DSH Interactive Control Uses the Human Browser's Native Session | Human and Program Alternate Prompts | Hermetic + Native | `test_browser_api_alternation_navigation_and_independent_auth`. |
| DSH Interactive Control Uses the Human Browser's Native Session | Human Opens Another Browser Session | Hermetic + Native | `test_browser_api_alternation_navigation_and_independent_auth`. |
| Web Control Is Bound to a Live Execution Incarnation | Host Is Alive but the Native Agent Is Gone | Hermetic + Native | `test_native_authentication_and_cold_state_do_not_activate`; `test_native_reset_changes_only_the_conversation_and_agent_incarnation`. |
| Web Control Is Bound to a Live Execution Incarnation | A Session ID Is Reused After Restart | Hermetic + Native | `test_explicit_relaunch_restores_exact_history_under_fresh_execution_identity`; `test_native_protocol_owner_and_session_guards_precede_mutation`. |
| Ordinary Web Admission Is Atomic at Native Handoff | Human Starts Work During Programmatic Preparation | Hermetic + Native | `test_browser_wins_after_api_readiness_before_native_handoff`; `test_program_wins_while_browser_input_is_still_preparing`. |
| Ordinary Web Admission Is Atomic at Native Handoff | The Native Inbox Already Contains Input | Hermetic + Native | `test_browser_queue_progress_and_exact_human_turn_interruption`; `test_native_program_first_allows_human_queue_and_scoped_interrupt`. |
| Explicit Operator Policies Retain Distinct Meanings | Operator Explicitly Queues While Busy | Hermetic + Native | `test_native_operator_queue_and_abandonment_are_attempt_scoped`; `test_web_explicit_operator_policy_is_forwarded_only_when_requested`. |
| Explicit Operator Policies Retain Distinct Meanings | Forced Policy Does Not Override Availability | Hermetic + Native | `test_native_guarded_refusals_do_not_insert`; `test_native_protocol_owner_and_session_guards_precede_mutation`. |
| Native Admission and Shared Activity Are Separately Observable | Human Steering Contributes to a Managed Turn | Hermetic + Native | `test_native_web_human_steering_shares_one_managed_charge`; `test_native_input_claims_preserve_mixed_turn_and_separate_human_followup`. |
| Native Admission and Shared Activity Are Separately Observable | Admission Reply Is Lost | Hermetic + Native | `test_native_admission_receipts_are_exact_and_payload_free`; `test_native_concurrent_duplicate_operations_insert_exactly_once`; `test_claimed_crash_restores_terminal_receipt_from_exact_native_journal`. |
| Web Interruption Targets the Intended Live Activity | Operator Interrupts Human-Started Work | Hermetic + Native | `test_browser_queue_progress_and_exact_human_turn_interruption`. |
| Web Interruption Targets the Intended Live Activity | Late Request Cancellation Finds Another Turn | Hermetic + Native | `test_native_operator_queue_and_abandonment_are_attempt_scoped`; `test_native_program_first_allows_human_queue_and_scoped_interrupt`. |
| Web Failure Never Replays an Ordinary Message | Agent Dies After Native Admission | Hermetic + Native | `test_native_pre_activation_recovery_removes_only_abandoned_ordinary_input`; `test_web_ordinary_event_native_refusal_or_execution_loss_never_replays`. |
| Web Failure Never Replays an Ordinary Message | Recovery Finds Both Human and Abandoned Program Input | Hermetic + Native | `test_native_pre_activation_recovery_removes_only_abandoned_ordinary_input`. |
| Browser and Program Use Independent Authorized Connections | Browser Answers While Houmao Observes | Hermetic + Native | `test_as_is_browser_answers_question_while_api_only_observes`. |
| Browser and Program Use Independent Authorized Connections | API Connection Credentials Expire | Hermetic + Native | `test_native_admission_receipts_are_exact_and_payload_free`; `test_browser_api_alternation_navigation_and_independent_auth`. |
| Web Lifecycle and Unsupported Controls Are Explicit | Raw Keystrokes Target a Web Agent | Hermetic + Native | `test_web_terminal_routes_explicitly_report_supported_native_inspection`; `test_owned_web_gateway_plugin_and_public_requests_share_native_state_without_replay_queue`. |
| Web Lifecycle and Unsupported Controls Are Explicit | Operator Relaunches the Managed Web Host | Hermetic + Native | `test_explicit_relaunch_restores_exact_history_under_fresh_execution_identity`; `test_native_web_fixture_keeps_one_browser_api_session`. Outer manager Messages and Chat cases also passed. |

### managed-agent-detailed-state

| Requirement | Scenario | Evidence Layer | Evidence and Limits |
| --- | --- | --- | --- |
| Managed agents expose a transport-specific detailed state route | Caller inspects TUI detail through the managed-agent namespace | Hermetic + Native | `test_managed_state_returns_tui_summary`; `test_current_detail_returns_full`. |
| Managed agents expose a transport-specific detailed state route | Caller inspects headless detail through the managed-agent namespace | Hermetic + Native | `test_managed_state_detail_returns_headless_view`. |
| Managed agents expose a transport-specific detailed state route | Caller Inspects a DSH Interactive Web Agent | Hermetic + Native | `test_manager_native_web_detail_uses_fresh_structured_state_without_terminal_or_headless_fabrication`; `test_web_passive_routes_share_native_detail_without_terminal_fields`. |
| Detailed state preserves TUI canonicality while giving headless parity | TUI detail remains canonical while managed-agent detail stays discoverable | Hermetic + Native | `test_success_returns_detail`; `test_detail_includes_probe_and_parsed_surface`. |
| Detailed state preserves TUI canonicality while giving headless parity | Headless rich state is available without a fake terminal route | Hermetic + Native | `test_managed_state_detail_returns_headless_view`. |
| Detailed state preserves TUI canonicality while giving headless parity | Web Transport Fails Independently of Its Supervisor | Hermetic + Native | `test_unavailable_web_sources_clear_stale_idle_without_cold_activation`; `test_actual_native_api_revocation_discards_prior_ready_projection`. |
| Web Detail Exposes Native Execution and Interaction Facts | Human Approval Is Pending | Hermetic + Native | `test_as_is_browser_answers_question_while_api_only_observes`; `test_native_interactions_refresh_without_state_sequence_or_browser_draft_invention`. |
| Web Detail Exposes Native Execution and Interaction Facts | Human Has an Unsubmitted Browser Draft | Hermetic + Native | `test_browser_api_alternation_navigation_and_independent_auth`; `test_native_interactions_refresh_without_state_sequence_or_browser_draft_invention`. |
| Web Detail Exposes Native Execution and Interaction Facts | Gateway Observation Falls Behind | Hermetic + Native | `test_native_web_baseline_gap_reconciliation_and_repeats_keep_bounded_identity`; `test_native_history_gap_or_rebinding_requires_verified_reconciliation`. |

### passive-server-tui-observation

| Requirement | Scenario | Evidence Layer | Evidence and Limits |
| --- | --- | --- | --- |
| Passive server creates and removes per-agent TUI observers based on the discovery index | Observer created when agent is discovered | Existing terminal regression | `test_creates_observer_for_discovered_agent`. |
| Passive server creates and removes per-agent TUI observers based on the discovery index | Observer removed when agent disappears | Existing terminal regression | `test_removes_observer_when_agent_disappears`. |
| Passive server creates and removes per-agent TUI observers based on the discovery index | Observer is not duplicated for an already-observed agent | Existing terminal regression | `test_keeps_existing_observer`. |
| Passive server creates and removes per-agent TUI observers based on the discovery index | DSH Web Has a Supervisory Terminal | Hermetic + Native | `test_supervisor_tmux_never_creates_a_terminal_parser_for_web`. |
| Compact agent state endpoint returns observation summary | Compact state returned for observed agent | Existing terminal regression | `test_success_returns_compact_state`. |
| Compact agent state endpoint returns observation summary | Compact state omits probe and parsed surface | Existing terminal regression | `test_current_state_returns_compact`. |
| Compact agent state endpoint returns observation summary | Agent not found returns 404 | Existing terminal regression | `test_not_found_returns_404`. |
| Compact agent state endpoint returns observation summary | Compact Web State Is Available Without a Terminal Observer | Hermetic + Native | `test_web_passive_routes_share_native_detail_without_terminal_fields`; `test_gateway_to_direct_fallback_preserves_native_identity_and_history`. |
| Detailed agent state endpoint returns full observation | Detail state includes probe and parsed surface | Existing terminal regression | `test_detail_includes_probe_and_parsed_surface`. |
| Detailed agent state endpoint returns full observation | Detail state with diagnostics-only observation | Existing terminal regression | `test_records_tui_down`. |
| Detailed agent state endpoint returns full observation | Web Detail Does Not Contain Parsed Console State | Hermetic + Native | `test_web_passive_routes_share_native_detail_without_terminal_fields`. |
| Agent history endpoint returns recent transitions | History returns recent transitions | Existing terminal regression | `test_history_most_recent_first`; `test_success_returns_history`. |
| Agent history endpoint returns recent transitions | History respects limit parameter | Existing terminal regression | `test_history_respects_limit`; `test_limit_query_parameter`. |
| Agent history endpoint returns recent transitions | Human Web Input Changes Shared History | Hermetic + Native | `test_actual_native_web_projection_tracks_shared_work_inbox_and_terminal_identity`; `test_browser_queue_progress_and_exact_human_turn_interruption`. |

### test-agent-launch-fixtures

| Requirement | Scenario | Evidence Layer | Evidence and Limits |
| --- | --- | --- | --- |
| Fixture qualification records actual evidence and limitations | Self-hosted endpoint is not configured | Fixtures + Browser | `test_web_live_runner_refuses_ambient_auth_and_validates_only_selected_file`; `test_live_runner_needs_explicit_external_credentials`. Real self-hosted live lane remains `not_run` without a selected compatible deployment/model. |
| Fixture qualification records actual evidence and limitations | Historical capture records Qwen usage | Fixtures + Browser | `test_real_two_turn_capture_assembles_native_requests_without_replay`. |
| Fixture qualification records actual evidence and limitations | DSH Headless Qualification Does Not Imply Interactive Support | Fixtures + Browser | `test_native_fixture_exact_resume`; `test_web_live_runner_refuses_ambient_auth_and_validates_only_selected_file`. |
| Fixture qualification records actual evidence and limitations | DSH TUI Qualification Uses the Native Web Surface | Fixtures + Browser | `test_native_web_fixture_keeps_one_browser_api_session`; `test_browser_api_alternation_navigation_and_independent_auth`. |
| DSH Web Fixtures Share the Existing Generic Endpoint Cases | A Fresh Host Uses Cloud DSH Interactively | Fixtures + Browser | `test_web_preparation_reuses_explicit_cases_and_operator_posture`; `test_native_web_fixture_keeps_one_browser_api_session`. |
| DSH Web Fixtures Share the Existing Generic Endpoint Cases | A Browser Connects to the Managed Fixture | Fixtures + Browser | `test_native_web_fixture_keeps_one_browser_api_session`; `test_browser_handoff_is_deliberate_private_and_origin_bound`. |
| DSH Web Qualification Exercises Mixed Control and Admission Races | Browser and Program Both Drive the Session | Fixtures + Browser | `test_browser_api_alternation_navigation_and_independent_auth`; `test_native_web_fixture_keeps_one_browser_api_session`. |
| DSH Web Qualification Exercises Mixed Control and Admission Races | Browser Input Races Ordinary Programmatic Delivery | Fixtures + Browser | `test_browser_wins_after_api_readiness_before_native_handoff`; `test_program_wins_while_browser_input_is_still_preparing`. |
| DSH Web Qualification Exercises Mixed Control and Admission Races | Restart Follows Uncertain Admission | Fixtures + Browser | `test_native_pre_activation_recovery_removes_only_abandoned_ordinary_input`; `test_web_ordinary_event_native_refusal_or_execution_loss_never_replays`. |
| DSH Web Qualification Exercises Mixed Control and Admission Races | No Real Account Exists in CI | Fixtures + Browser | `test_browser_api_alternation_navigation_and_independent_auth`; `test_web_live_runner_refuses_ambient_auth_and_validates_only_selected_file`. |

## Acceptance State

The table has 96 scenario rows with concrete test references. Full unit/static/native and real DeepSeek Web gates passed. Strict docs, distribution build/Twine metadata, and current-byte inventory audits passed. Wheel and sdist each contain 992 files, including all 18 required DSH product resources; no fixture, reference checkout, private state, or other non-product tree entered either artifact. Local-link checks covered 57 changed Markdown files and 220 links. The secret/path audit checked 212 changed source/documentation files, including TypeScript, with no findings; local credential files and paid runs were excluded from reads. Both scenario maps contain exactly 61 and 96 rows, with 81 and 87 valid named test references and no gaps or duplicate rows.

OpenSpec validation is versioned. All 241 current main specifications validate normally, and change 02 passes strict validation. Accepted change 01 passes strict validation against its SHA-verified captured 240-spec predecessor baseline with zero issues. Comparing that historical full-block delta against the post-Web main store reports one expected mismatch: its fixture-qualification block predates change 02's new Web TUI qualification scenario. The accepted 61-scenario delta remains unchanged. Scoped main warnings remain at the 135-warning baseline, global warnings remain at 1,294, and the Web sync introduced no new main-spec errors or warnings. Current-store `openspec validate --all --json` passes 242 of 243 items and exits 1 solely for that historical mismatch. These results do not claim that both historical and current changes simultaneously pass validation against the current store.

Both implementations and their acceptance evidence are complete. Configured self-hosted live qualification remains separate; unavailable prerequisites do not become a passing lane. Web main-spec synchronization is complete. Review and archive remain explicit workflow follow-ups; no external issue was changed by this acceptance record.
