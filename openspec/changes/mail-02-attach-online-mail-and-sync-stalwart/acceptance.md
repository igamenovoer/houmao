# Mail Change 02 Acceptance Evidence

This inventory covers every requirement and scenario in all eight delta capabilities: 36 requirements and 66 scenarios. Evidence IDs resolve to exact durable pytest nodes or explicitly scoped qualification/load artifacts below. Multiple IDs denote composed checks, not an assertion that one end-to-end test exercised every clause.

## Scope and Measured Limits

Change 01 is the synchronized foundation. This change adds existing-account online attachment, finite metadata pages, account-scoped incremental observation, and cycle-scoped periodic reminders. The user clarification is preserved: unchanged eligible inbox work can remind again at later intervals. Same-cycle duplicate admission and overlapping attempts remain suppressed.

Runtime integrations use real loopback HTTP and a real independent stand-in body process/PID/conversation marker. They do not claim an autonomous real-LLM conversation. Provider wire tests use a deterministic fake server. Skill evidence validates installed instructions, projection/routing, and underlying API behavior; it does not prove a model autonomously follows every workflow step.

See [qualification.md](qualification.md) for sanitized actual-service reports and final aggregate checks. The representative raw/runtime reports are distinct from the unexecuted 100-agent/million-message workload plan. Metadata/page counts are bounded observations, never invented exact inbox totals. No capacity claim follows from the small live checks.

## Repeatable Checks

```bash
pixi run pytest tests/unit/mailbox tests/unit/agents/test_mailbox_runtime_support.py -q --tb=short
pixi run pytest tests/unit/agents/realm_controller/test_notifier_bounded_sync.py tests/integration/mailbox/test_online_runtime_contract.py tests/integration/mailbox/test_online_authority_process.py -q --tb=short
pixi run test
pixi run lint
pixi run typecheck
git diff --check
openspec validate mail-02-attach-online-mail-and-sync-stalwart --strict --json
```

The mailbox plus runtime-skill projection check passed 221 cases before the final context-local meter and additional regressions. Final aggregate results belong to qualification.md. Owned sync/helper tests, raw HTTP checkpoint tests, the readonly metrics runner, strict typing, schema examples, relative links, and the developer skill validator were also exercised during implementation.

## Final Aggregate Results

After the final effect-lease, credential-outage, and query-policy race fixes, `pixi run test -q --tb=line` passed 3,651 tests with 14 skips. The affected offline/online mailbox and gateway/mailbox/registry runtime integration command passed 29 tests. Ruff, strict mypy (449 source files), formatting checks, `git diff --check`, and strict OpenSpec validation passed. Warnings were the existing FastAPI/httpx test-client deprecation. See [qualification.md](qualification.md#repository-checks) for exact counts, timings, local logs, and the final repeated live runtime result.

## Evidence Catalog

### P1: Strict Metadata Pages and Scoped Continuation

- [tests/unit/mailbox/test_pagination.py](../../../tests/unit/mailbox/test_pagination.py)::test_list_defaults_are_finite_and_removed_body_input_is_explicit
- [tests/unit/mailbox/test_pagination.py](../../../tests/unit/mailbox/test_pagination.py)::test_local_metadata_pages_have_scoped_continuation_and_page_counts
- [tests/unit/mailbox/test_pagination.py](../../../tests/unit/mailbox/test_pagination.py)::test_cursor_filter_owner_and_mutation_are_refused
- [tests/unit/mailbox/test_scope.py](../../../tests/unit/mailbox/test_scope.py)::test_reference_cannot_cross_scope

### W1: Wire Filters, Metadata Only, and Connection Reuse

- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_server_filters_precede_limit_and_metadata_never_requests_body
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_missing_role_never_widens_to_account_query
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_since_is_exclusive_and_membership_preserves_multiple_mailboxes
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_discovery_pins_exact_identity_and_reuses_account_and_roles

### W2: Discovery, Selected Accounts, and Immutable Credentials

- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_ambiguous_accounts_and_wrong_explicit_account_never_choose_first
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_sender_mismatch_does_not_fall_back_to_first_identity
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_credential_epoch_is_immutable_after_source_replacement
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_unapproved_origin_and_redirect_never_receive_provider_credentials

### W3: Wire Cursor State, Provider Caps, and Refresh

- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_provider_cap_uses_bounded_probe_and_rejects_state_drift
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_probe_budget_is_conservative_instead_of_false_end
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_same_account_credential_refresh_preserves_scoped_provider_cursor

- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_wire_role_refresh_between_scope_and_query_cannot_publish_old_policy
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_query_policy_change_inside_commit_guard_keeps_old_snapshot
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_role_policy_change_before_final_revalidation_publish_discards_work

### W4: Content Limits and Mutation Outcomes

- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_content_truncation_and_multipart_budget_are_visible_and_nonmutating
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_send_checks_submission_failure_and_does_not_retry
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_send_retains_uncertainty_or_confirmed_receipt_after_failure
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_reply_uses_metadata_and_marks_parent_only_after_confirmed_submission

### S1: Bootstrap Boundary, Intermediate Progress, and Restart

- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_bootstrap_boundary_precedes_query_and_interleaved_arrival
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_intermediate_checkpoint_survives_restart_without_borrowing_get_state
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_wire_observer_preserves_pre_query_boundary_and_intermediate_state

### S2: Atomic Checkpoint Reconciliation and Retry

- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_fetch_failure_keeps_batch_retryable_and_sanitizes_backoff
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_authoritative_not_found_and_destroyed_remove_before_checkpoint
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_unreconciled_metadata_does_not_advance_checkpoint
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_failed_local_transaction_keeps_metadata_and_checkpoint_together
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_wire_observer_failed_fetch_keeps_checkpoint_until_reconciled_retry

### S3: Finite Rebase, Query Deltas, Backoff, and Time

- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_stale_or_unsupported_changes_rebases_bounded_filtered_view
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_qualified_query_changes_errors_use_one_bounded_requery
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_query_state_progress_never_becomes_an_email_checkpoint
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_provider_smaller_get_cap_bounds_changes_and_metadata_batch
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_time_budget_yields_after_durable_boundary_without_another_request
- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_wire_observer_expired_checkpoint_uses_finite_filtered_rebase

### S4: Disposable Bounded Cache and Account Isolation

- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_binding_account_and_query_policy_scopes_do_not_share_overlap_ids
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_cache_eviction_is_a_sample_and_never_confirmed_loss_of_eligibility
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_disposable_cache_loss_or_invalid_json_rebases_without_reconstructing_mail_truth
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_persistence_excludes_bodies_credentials_and_bounds_preview
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_status_after_restart_is_safe_and_scoped_without_network

### F1: Superseded Observation and Compaction Revalidation

- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_superseded_worker_never_commits_or_exposes_old_metadata
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_final_fence_rejects_late_revalidation_and_wakeup
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_revalidation_preserves_evicted_eligible_compaction_and_clears_confirmed_loss
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_revalidation_cursor_rotates_across_restart_with_only_one_remaining_get
- [tests/unit/mailbox/test_sync.py](../../../tests/unit/mailbox/test_sync.py)::test_no_remaining_budget_preserves_uncertain_compaction_memory

### B1: Attach, Refresh, Reconnect, Detach, and Private Sources

- [tests/unit/mailbox/test_online_binding.py](../../../tests/unit/mailbox/test_online_binding.py)::test_attach_refresh_reconnect_detach_preserve_offline_and_source
- [tests/unit/mailbox/test_online_binding.py](../../../tests/unit/mailbox/test_online_binding.py)::test_rejected_candidate_and_wrong_revision_leave_current_binding
- [tests/unit/mailbox/test_online_binding.py](../../../tests/unit/mailbox/test_online_binding.py)::test_explicit_replacement_and_refresh_reject_account_drift
- [tests/unit/mailbox/test_online_binding.py](../../../tests/unit/mailbox/test_online_binding.py)::test_private_source_validation_and_request_contract

### B2: Management CAS, Projection, and Retirement

- [tests/unit/mailbox/test_online_binding.py](../../../tests/unit/mailbox/test_online_binding.py)::test_competing_candidate_controls_have_one_cas_winner
- [tests/unit/mailbox/test_online_binding.py](../../../tests/unit/mailbox/test_online_binding.py)::test_post_commit_projection_failure_reports_confirmed_revision
- [tests/unit/mailbox/test_online_binding.py](../../../tests/unit/mailbox/test_online_binding.py)::test_started_mutation_outcome_stays_pinned_without_retry
- [tests/unit/mailbox/test_online_binding.py](../../../tests/unit/mailbox/test_online_binding.py)::test_late_observation_is_discarded_after_refresh_or_reconnect
- [tests/integration/mailbox/test_online_authority_process.py](../../../tests/integration/mailbox/test_online_authority_process.py)::test_cross_process_retirement_times_out_without_false_activation

### R1: Real HTTP Runtime and Stable Stand-in Body

- [tests/integration/mailbox/test_online_runtime_contract.py](../../../tests/integration/mailbox/test_online_runtime_contract.py)::test_disabled_running_body_attaches_refreshes_restarts_and_detaches

### R2: Replacement Cancels Pending and Late Provider Work

- [tests/integration/mailbox/test_online_runtime_contract.py](../../../tests/integration/mailbox/test_online_runtime_contract.py)::test_replacement_cancels_pending_and_discards_late_provider_poll
- [tests/integration/mailbox/test_online_runtime_contract.py](../../../tests/integration/mailbox/test_online_runtime_contract.py)::test_started_prompt_effect_prevents_false_replacement_activation
- [tests/integration/mailbox/test_online_runtime_contract.py](../../../tests/integration/mailbox/test_online_runtime_contract.py)::test_replacement_between_origin_check_and_effect_cannot_dispatch_old_prompt

### N1: Atomic Per-Cycle Admission and Stale Pending Scope

- [tests/unit/agents/realm_controller/test_notifier_bounded_sync.py](../../../tests/unit/agents/realm_controller/test_notifier_bounded_sync.py)::test_cycle_and_pending_request_admission_commit_atomically
- [tests/unit/agents/realm_controller/test_notifier_bounded_sync.py](../../../tests/unit/agents/realm_controller/test_notifier_bounded_sync.py)::test_unchanged_mail_reminds_each_due_cycle_and_old_pending_scope_is_rejected
- [tests/unit/agents/realm_controller/test_notifier_bounded_sync.py](../../../tests/unit/agents/realm_controller/test_notifier_bounded_sync.py)::test_origin_storage_failure_refuses_dispatch_without_killing_fence_checks

### N2: Busy Admission, Periodic Online Reminders, and Compaction

- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_stalwart_adapter_defers_then_repeats_for_unchanged_unread_mail
- [tests/unit/agents/realm_controller/test_gateway_dual_mail.py](../../../tests/unit/agents/realm_controller/test_gateway_dual_mail.py)::test_channels_keep_independent_configuration_and_periodic_reminders
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_pre_notification_compaction_does_not_repeat_for_unchanged_mail
- [tests/unit/agents/realm_controller/test_gateway_dual_mail.py](../../../tests/unit/agents/realm_controller/test_gateway_dual_mail.py)::test_online_canonical_change_preserves_offline_compaction_eligibility
- [tests/unit/agents/realm_controller/test_notifier_bounded_sync.py](../../../tests/unit/agents/realm_controller/test_notifier_bounded_sync.py)::test_online_credential_outage_preserves_enabled_notifier_and_recovers

### G1: Gateway and Scoped Operator Controls

- [tests/unit/mailbox/test_online_surfaces.py](../../../tests/unit/mailbox/test_online_surfaces.py)::test_gateway_live_controls_require_revision_and_preserve_body
- [tests/unit/mailbox/test_online_surfaces.py](../../../tests/unit/mailbox/test_online_surfaces.py)::test_gateway_client_uses_strict_typed_body
- [tests/unit/mailbox/test_online_surfaces.py](../../../tests/unit/mailbox/test_online_surfaces.py)::test_scoped_online_cli_forwards_pinned_control
- [tests/unit/mailbox/test_online_surfaces.py](../../../tests/unit/mailbox/test_online_surfaces.py)::test_gateway_preserves_uncertain_send_receipt_in_old_binding

### C1: Finite CLI Page Forwarding and Removed Body Flag

- [tests/unit/srv_ctrl/commands/test_mail_channel_commands.py](../../../tests/unit/srv_ctrl/commands/test_mail_channel_commands.py)::test_cli_forwards_finite_metadata_page_and_exact_cursor
- [tests/unit/srv_ctrl/commands/test_mail_channel_commands.py](../../../tests/unit/srv_ctrl/commands/test_mail_channel_commands.py)::test_cli_rejects_list_body_flag_with_explicit_content_guidance

### X1: Proxy Page/Conflict Preservation

- [tests/unit/passive_server/test_app_contracts.py](../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailListEndpoint::test_returns_200_with_mocked_client
- [tests/unit/passive_server/test_app_contracts.py](../../../tests/unit/passive_server/test_app_contracts.py)::test_mail_proxy_preserves_structured_stale_cursor_conflict
- [tests/unit/server/test_app_contracts.py](../../../tests/unit/server/test_app_contracts.py)::test_server_mail_proxy_preserves_structured_stale_cursor_conflict
- [tests/unit/mailbox/test_online_surfaces.py](../../../tests/unit/mailbox/test_online_surfaces.py)::test_pair_clients_preserve_control_body_and_escape_target

### O1: Registry-only Route and Credential Boundary

- [tests/unit/mailbox/test_offline_registry.py](../../../tests/unit/mailbox/test_offline_registry.py)::test_narrow_route_inventory_and_redacted_validation

### K1: Installed Skill Contract and Native/API Routing

- [tests/unit/agents/test_mailbox_runtime_support.py](../../../tests/unit/agents/test_mailbox_runtime_support.py)::test_install_runtime_mailbox_system_skills_for_tool_projects_gateway_and_transport_docs
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_falls_back_when_required_skill_is_missing
- [tests/unit/srv_ctrl/commands/test_mail_channel_commands.py](../../../tests/unit/srv_ctrl/commands/test_mail_channel_commands.py)::test_fresh_send_rejects_replaced_binding_before_backend_io
- Installed instruction artifacts: [ordinary mail routine](../../../src/houmao/agents/assets/system_skills/public/houmao-shared-routines/subskills/houmao-agent-email-comms/SKILL-MAIN.md), [notified round routine](../../../src/houmao/agents/assets/system_skills/public/houmao-shared-routines/subskills/houmao-process-emails-via-gateway/SKILL-MAIN.md), and [development fixture mail attachment](../../../skillset/dev/houmao-dev-launch-agents/commands/attach-online-mail.md). Static instructions and API/projection tests are the asserted boundary.

### A1: Explicit Provisioning Entry Boundary

- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_launch_prepares_both_slots_for_one_owner
- [tests/unit/mailbox/test_online_binding.py](../../../tests/unit/mailbox/test_online_binding.py)::test_explicit_administrative_provisioning_creates_once_without_reentry_rotation
- The explicit provisioning test invokes the real ensure/management workflow with HTTP principal persistence replaced by a deterministic fake. It verifies first creation, idempotent reentry, reused credential bytes/reference, and no implicit rotation; attachment is separately qualified with normal-account credentials.

### L1: Sanitized Representative Live Qualification

- [Actual-service qualification](qualification.md): sanitized normal-account client, readonly observation metrics, and runtime attachment/reminder evidence. Retain the actual release, accounts, scale, body type, and limitations stated there.

### L2: Unexecuted Target-Scale Plan and Measured Readonly Runner

- [tests/unit/mailbox/test_stalwart_jmap.py](../../../tests/unit/mailbox/test_stalwart_jmap.py)::test_readonly_qualification_reports_actual_counts_and_unmeasured_reminders
- [Qualification and target-scale plan](../../../docs/reference/mailbox/operations/stalwart-qualification.md), [sync checkpoint contract](../../../docs/reference/mailbox/internals/stalwart-sync.md), and [readonly metrics runner](../../../scripts/qualification/stalwart-mail/observe.py). Large-archive/100-agent/million-message comparison is a documented unexecuted workload, not an already measured result. The readonly runner marks gateway reminder counts unavailable; runtime qualification measures them separately.

## Complete Scenario Inventory

### agent-gateway-mail-notifier

[Spec delta](specs/agent-gateway-mail-notifier/spec.md)

| Requirement | Named Scenario | Evidence |
| --- | --- | --- |
| Online notifier observes bounded metadata work | Large retained history does not trigger body scans | W1, S3, L2 |
| Online notifier observes bounded metadata work | Body is busy after metadata synchronization | N2, R1 |
| Reminder deduplication remains cycle-scoped | Unchanged online mail repeats at later intervals | N2, L1 |
| Reminder deduplication remains cycle-scoped | Same cycle is retried after reconnect | N1 |
| Online notifier work is fenced to its binding | Replacement occurs before queued reminder dispatch | R2, F1 |
| Sync recovery preserves compaction eligibility truth | Cached entry is evicted and rediscovered | F1, N2 |

### agent-mailbox-protocol

[Spec delta](specs/agent-mailbox-protocol/spec.md)

| Requirement | Named Scenario | Evidence |
| --- | --- | --- |
| Shared mailbox listing returns bounded metadata pages | Default list is bounded | P1 |
| Shared mailbox listing returns bounded metadata pages | Caller requests bodies through list | P1, C1 |
| Shared mailbox listing returns bounded metadata pages | Peek remains non-mutating | W4, R1 |
| Pagination counts and continuation scope are explicit | Page is not the whole inbox | P1 |
| Pagination counts and continuation scope are explicit | Offline cursor is supplied to online list | P1, W3 |
| Mailbox content limits are visible | Large body is truncated by the provider | W4 |

### agent-mailbox-stalwart-transport

[Spec delta](specs/agent-mailbox-stalwart-transport/spec.md)

| Requirement | Named Scenario | Evidence |
| --- | --- | --- |
| Stalwart-backed mailbox transport provisions mailbox principals through server-owned management surfaces | Starting a Stalwart-backed session provisions a missing mailbox account | A1 |
| Stalwart-backed mailbox transport provisions mailbox principals through server-owned management surfaces | Restarting the same Stalwart-backed mailbox principal is idempotent | A1 |
| Stalwart-backed mailbox transport provisions mailbox principals through server-owned management surfaces | Restarting the same Stalwart-backed mailbox principal reuses credential references without unnecessary rotation | B1, W2 |
| Stalwart-backed mailbox transport provisions mailbox principals through server-owned management surfaces | Hub-managed account attaches without management credentials | R1, L1 |
| Stalwart discovery distinguishes session and request endpoints | Discovery advertises a different API path | W1, W2 |
| Stalwart account and sending identity match the binding | Login name differs from the sending address | W2 |
| Stalwart account and sending identity match the binding | Multiple accounts have no unambiguous selection | W2 |

### agent-mailbox-system-skills

[Spec delta](specs/agent-mailbox-system-skills/spec.md)

| Requirement | Named Scenario | Evidence |
| --- | --- | --- |
| Mailbox routines triage bounded metadata pages | Inbox is larger than one processing round | K1, L2 |
| Mailbox routines triage bounded metadata pages | Metadata is insufficient for a selected task | K1, W4 |
| Online binding changes end stale processing rounds explicitly | Account changes before a fresh reply or send | K1, R2 |
| Runtime mailbox guidance keeps credential administration outside ordinary mail work | Online authentication expires during a round | K1, R1 |

### houmao-srv-ctrl-native-cli

[Spec delta](specs/houmao-srv-ctrl-native-cli/spec.md)

| Requirement | Named Scenario | Evidence |
| --- | --- | --- |
| Scoped online mailbox commands manage live account bindings | Operator attaches a hub-provisioned account | G1, R1 |
| Scoped online mailbox commands manage live account bindings | Refresh rejects another account | G1, B1 |
| Scoped online mailbox commands manage live account bindings | Detached provider mail is retained | G1, R1 |
| Native mailbox listing is paged and metadata-only | Operator continues an online metadata page | C1, W3 |
| Native mailbox listing is paged and metadata-only | Removed content-list flag is used | C1 |
| Online management reports committed and uncertain outcomes safely | Projection fails after activation | B2, G1 |

### online-mail-attachment

[Spec delta](specs/online-mail-attachment/spec.md)

| Requirement | Named Scenario | Evidence |
| --- | --- | --- |
| Existing agents can attach externally provisioned online mail | Hub account attaches to a mailbox-disabled body | R1, L1 |
| Existing agents can attach externally provisioned online mail | Agent retains offline mail | R1, B1 |
| Candidate validation precedes online binding activation | Invalid key leaves existing bindings intact | R1, B1 |
| Candidate validation precedes online binding activation | Endpoint is unavailable | R1 |
| Candidate validation precedes online binding activation | Account does not match the requested address | W2, B1 |
| Live online controls are owned and revision-checked | Concurrent management updates conflict | B2 |
| Live online controls are owned and revision-checked | Address change is not an implicit replacement | B1 |
| Credential refresh preserves account identity and private material | Hub rotates a mailbox credential | B1, W3, R1 |
| Credential refresh preserves account identity and private material | Refresh resolves another account | B1 |
| Superseded online operations cannot target replacement accounts | Old poll completes after replacement | R2, F1 |
| Superseded online operations cannot target replacement accounts | Send result is uncertain during retirement | B2, W4 |
| Detach and reconnect preserve lifecycle boundaries | Online detach restores offline canonical identity | R1 |
| Detach and reconnect preserve lifecycle boundaries | Provider outage is recoverable without identity change | R1, N2 |
| Gateway facade and notifier become usable without body relaunch | Gateway companion is attached after body launch | R1, L1 |
| Gateway facade and notifier become usable without body relaunch | No native mailbox skill route is available | K1 |

### passive-server-gateway-proxy

[Spec delta](specs/passive-server-gateway-proxy/spec.md)

| Requirement | Named Scenario | Evidence |
| --- | --- | --- |
| Online binding controls proxy the owning gateway authority | Refresh through the passive server preserves scope | X1, G1 |
| Online binding controls proxy the owning gateway authority | Binding changed before proxy reaches the gateway | X1, G1 |
| Mail proxies preserve page and synchronization information | Continued page passes through unchanged | X1, C1 |
| Mail proxies preserve page and synchronization information | Stale cursor is not a connectivity error | X1 |
| Registry-only service mode exposes no online binding management | Offline member attempts online replacement | O1 |

### stalwart-mailbox-sync

[Spec delta](specs/stalwart-mailbox-sync/spec.md)

| Requirement | Named Scenario | Evidence |
| --- | --- | --- |
| Stalwart list queries are bounded and filtered on the server | Old unread mail is behind newer read mail | W1 |
| Stalwart list queries are bounded and filtered on the server | Inbox role is absent | W1 |
| Metadata discovery never retrieves message body values | Metadata page has no body transfer | W1, S1 |
| Metadata discovery never retrieves message body values | Explicit content exceeds a supported limit | W4 |
| Continuation cursors preserve query and account scope | Credential refresh keeps a valid account cursor | W3 |
| Continuation cursors preserve query and account scope | Filter changes invalidate continuation | W3, P1 |
| Continuation cursors preserve query and account scope | Mail changes between pages | W3 |
| Discovery and mailbox-role lookup are reused per connection scope | A multi-message page avoids per-message role queries | W1 |
| Incremental checkpoints are account-scoped and distinct from query state | Changes have intermediate states | S1 |
| Incremental checkpoints are account-scoped and distinct from query state | Account replacement has overlapping provider IDs | S4 |
| Applied metadata and checkpoint progress commit together | Fetch fails after a change response | S2 |
| Applied metadata and checkpoint progress commit together | Message disappears before metadata retrieval | S2 |
| Stale-state recovery has finite work budgets | Old checkpoint cannot be calculated | S3 |
| Stale-state recovery has finite work budgets | Query delta exceeds the maximum | S3 |
| Metadata view eviction does not redefine mailbox truth | Eligible mail falls outside the cached window | S4, F1 |
| Synchronization status exposes bounded progress and limitations | Catch-up spans several cycles | S1, S3, S4 |
| Qualification measures retained-history independence | Idle mailbox has a large archive | L2, L1, W1 |

## Acceptance Boundaries

All configured channels, continuation values, message references, and pending reminder origins remain scoped to owner and binding. Refresh/reconnect preserves same-account identity; explicit replacement starts another scope. Offline mail and externally owned credential sources survive online detach. Selected content exposes truncation; list/sync does not retrieve body values. Failed or uncertain mutation outcomes remain pinned and are not automatically replayed.

Request/time limits are finite client work budgets, not provider-capacity guarantees. Connection validation is separately finite/cached per immutable epoch; warmed observation plus remembered-eligibility work share five JMAP methods and ten seconds by default. Optional queryChanges has no email-change pagination promise and is disabled unless qualified. Missing/evicted metadata never means completed work or a new compaction eligibility stretch.

Issue #79/#80 closure requires reviewing this map and qualification.md together. Archive, main-spec synchronization, commit/push, and GitHub issue closure remain separately authorized workflows.
