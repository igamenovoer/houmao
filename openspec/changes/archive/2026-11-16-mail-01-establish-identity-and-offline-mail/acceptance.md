# Acceptance Evidence for Mail Change 01

This map covers the exact headings in all 14 spec deltas: 90 requirement operations and 209 named scenarios. Each requirement row lists every scenario beneath it and the evidence groups used to assess it. Removed requirements are tracked as intentional removals, with replacement/rejection coverage rather than support for the removed behavior.

Evidence combines hermetic component tests, HTTP contract tests, and isolated subprocess integrations. A row citing multiple groups is a composed verification: those groups prove different portions of the contract. It does not assert that every named scenario has a separate end-to-end test or that every behavior ran against a real provider.

## Execution and Practical Limits

Use Pixi for all checks. The tests create explicitly fake credentials in pytest temporary directories outside the checkout. This document records test names and sanitized outcomes only; it contains no credential values, request headers, private run payloads, or authorization verifiers.

The registry process integration uses the supported `houmao-passive-server offline-registry` command, real loopback HTTP, disjoint registry/agent filesystem roots, and independent child processes. The remote runtime test keeps a real stand-in body process alive and checks its PID/conversation identity through attachment and reconciliation. These tests establish process and filesystem independence on one physical test host. They do not claim a deployed multi-machine TLS service or a real AI-provider conversation.

Launch-time Stalwart construction is verified at the provisioning boundary with a hermetic provider stand-in. Existing Stalwart facade/notifier tests use mocked JMAP. Live online account attachment and wire-level incremental JMAP qualification remain change 02 work.

A globally unique `agent_id` is a system contract, not an empirically proven worldwide property. UUID/default selection, opaque supplied IDs, deterministic opt-in hashing, stable persistence, and same-owner idempotence are tested. Accidental global ID collision detection is deliberately outside this change.

## Repeatable Validation Commands

```bash
pixi run pytest tests/unit/mailbox tests/unit/passive_server tests/unit/server tests/unit/srv_ctrl/test_mailbox_commands.py tests/integration/mailbox/test_offline_registry_process.py -q --tb=short
pixi run pytest tests/unit/agents/realm_controller/test_agent_identity.py tests/unit/agents/test_brain_builder.py tests/unit/agents/realm_controller/test_runtime_agent_identity.py tests/unit/agents/realm_controller/test_mailbox_binding_authority.py tests/unit/agents/realm_controller/test_runtime_mailbox.py tests/unit/agents/realm_controller/test_runtime_registry.py tests/unit/agents/realm_controller/test_gateway_dual_mail.py -q --tb=short
pixi run pytest tests/unit/agents/realm_controller/test_gateway_support.py tests/unit/agents/test_mailbox_runtime_support.py tests/integration/agents/realm_controller/test_mailbox_runtime_contract.py -q --tb=short
pixi run test
pixi run lint
pixi run typecheck
git diff --check
openspec validate mail-01-establish-identity-and-offline-mail --strict --json
openspec validate --specs
```

Full unit-suite evidence from the main implementation run (`tests/unit`): **3,547 passed, 14 skipped**, completed in 67.02 seconds. The ten warnings concern the installed Starlette/httpx test-client deprecation. The skipped cases retain their existing skip conditions; this result does not claim they executed.

Focused validation also passed the real HTTP registry process tests, passive-server contracts, server contracts, and owned mailbox/admin suites during implementation. Strict change validation, repository lint, and `git diff --check` passed in the main implementation run. Full-project strict mypy passed for **438 source files**. The final affected integration run passed **22 cases** across the mailbox runtime, registry runtime, gateway runtime, and offline registry process files.

Follow-up validation after repairing the remaining live-gateway integration fixtures and safe CLI projection output: the gateway runtime integration file plus CLI unit file passed **33 cases**. The new typed/JSON public registry summary regression passed **2 cases** without accessing a manifest or private backend configuration.

The full unit result supersedes intermediate focused counts. Existing real-provider/load limits remain as stated above; a green unit suite does not measure provider capacity.

After the approved planning reconciliation, strict change validation passed with zero issues. Semantic synchronization applied all 14 capability deltas, including two new main specs, and preserved unrelated requirements and existing Purpose sections. The 90 requirement operations comprise 39 additions, 40 modifications, and 11 removals. Main-spec validation passed for all **232 specifications**; existing repository-wide placeholder/length warnings remain outside this change. Repeating the semantic merge produced no content changes.

The approved planning reconciliation explicitly replaces earlier-format compatibility and takeover promises. Format tests exercise legacy versions 1 and 2 and the current-format invariant; rejection of version 3 follows that same exact-version validator. Locking assessment combines process exclusion/recovery tests, release/history tests, and review of the shared address/index lock path. No separate synchronized delivery-versus-release stress result is claimed.

## Evidence Catalog

### I1: Creation Defaults and Supplied Identity

- [tests/unit/agents/realm_controller/test_agent_identity.py](../../../../tests/unit/agents/realm_controller/test_agent_identity.py)::test_creation_defaults_to_distinct_uuid_for_repeated_name
- [tests/unit/agents/realm_controller/test_agent_identity.py](../../../../tests/unit/agents/realm_controller/test_agent_identity.py)::test_creation_name_hash_is_explicit_and_deterministic
- [tests/unit/agents/realm_controller/test_agent_identity.py](../../../../tests/unit/agents/realm_controller/test_agent_identity.py)::test_supplied_identity_rejects_explicit_generation
- [tests/unit/agents/realm_controller/test_agent_identity.py](../../../../tests/unit/agents/realm_controller/test_agent_identity.py)::test_supplied_opaque_identity_is_preserved_without_generation

### I2: Creation, Reuse, and Non-Generating Reads

- [tests/unit/agents/test_brain_builder.py](../../../../tests/unit/agents/test_brain_builder.py)::test_brain_identity_creation_and_reuse
- [tests/unit/agents/realm_controller/test_runtime_agent_identity.py](../../../../tests/unit/agents/realm_controller/test_runtime_agent_identity.py)::test_template_start_generates_uuid_but_created_brain_preserves_identity
- [tests/unit/agents/realm_controller/test_runtime_agent_identity.py](../../../../tests/unit/agents/realm_controller/test_runtime_agent_identity.py)::test_created_brain_missing_identity_is_not_repaired_by_start
- [tests/unit/agents/realm_controller/test_runtime_agent_identity.py](../../../../tests/unit/agents/realm_controller/test_runtime_agent_identity.py)::test_existing_brain_does_not_generate_replacement_identity

### I3: Durable Identity and Presence Projections

- [tests/unit/agents/realm_controller/test_runtime_registry.py](../../../../tests/unit/agents/realm_controller/test_runtime_registry.py)::test_start_resume_send_prompt_and_stop_refresh_registry
- [tests/unit/agents/realm_controller/test_registry_storage.py](../../../../tests/unit/agents/realm_controller/test_registry_storage.py)::test_registry_publish_and_resolve_accepts_friendly_name
- [tests/unit/agents/realm_controller/test_registry_storage.py](../../../../tests/unit/agents/realm_controller/test_registry_storage.py)::test_known_registry_resolution_reports_name_ambiguity
- [tests/unit/agents/realm_controller/test_registry_storage.py](../../../../tests/unit/agents/realm_controller/test_registry_storage.py)::test_registry_schema_is_packaged_and_covers_optional_gateway_and_mailbox_groups

### B1: Slot Shapes and Canonical Identity

- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_canonical_identity_uses_configured_presence
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_slots_reject_mixed_owners_or_wrong_channel
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_wrong_persisted_channel_is_rejected
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_health_failures_preserve_both_configured_identities

### B2: Atomic Persistence and Revision Conflicts

- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_credential_revision_preserves_online_binding_and_offline_slot
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_stale_writer_and_detach_do_not_resurrect_bindings
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_process_mutations_are_serialized
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_interrupted_atomic_replace_preserves_original
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_stale_runtime_write_preserves_server_owned_authority
- [tests/unit/agents/realm_controller/test_runtime_mailbox.py](../../../../tests/unit/agents/realm_controller/test_runtime_mailbox.py)::test_controller_persistence_refreshes_cached_backend_binding

### B3: Launch Both Slots and Preserve Owner

- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_launch_prepares_both_slots_for_one_owner
- [tests/unit/passive_server/test_headless_service.py](../../../../tests/unit/passive_server/test_headless_service.py)::TestHeadlessLaunch::test_launch_forwards_stalwart_mailbox_options

### B4: Safe Projections and Reconciliation

- [tests/unit/agents/realm_controller/test_cli.py](../../../../tests/unit/agents/realm_controller/test_cli.py)::test_start_session_projects_safe_dual_mail_identity
- [tests/unit/server/test_service.py](../../../../tests/unit/server/test_service.py)::test_tui_mail_summary_uses_safe_registry_projection_without_manifest
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_registry_projection_excludes_secret_resolution_inputs
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_remote_binding_has_no_registry_filesystem_path
- [tests/unit/agents/realm_controller/test_mailbox_binding_authority.py](../../../../tests/unit/agents/realm_controller/test_mailbox_binding_authority.py)::test_binding_decode_does_not_materialize_credentials
- [tests/unit/agents/realm_controller/test_runtime_mailbox.py](../../../../tests/unit/agents/realm_controller/test_runtime_mailbox.py)::test_projection_failure_reports_committed_revision_and_reconciles
- [tests/unit/agents/realm_controller/test_runtime_registry.py](../../../../tests/unit/agents/realm_controller/test_runtime_registry.py)::test_attach_and_detach_gateway_refreshes_registry_payload

### O1: Atomic Claims and Recoverable Preparation

- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_preparing_claim_is_recoverable_and_excludes_other_owners
- [tests/integration/mailbox/test_offline_registry_process.py](../../../../tests/integration/mailbox/test_offline_registry_process.py)::test_concurrent_process_claims_have_one_winner
- [tests/integration/mailbox/test_offline_registry_process.py](../../../../tests/integration/mailbox/test_offline_registry_process.py)::test_killed_preparation_releases_os_locks_and_recovers_same_owner
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_operator_can_explicitly_release_interrupted_preparation

### O2: Membership, Authentication, and Credential Lifecycle

- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_membership_is_durable_and_join_retry_does_not_rotate
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_conflicting_owner_cannot_claim_address
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_sender_fields_and_stale_fresh_send_fail_before_delivery
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_explicit_credential_replacement
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_member_credential_is_created_once_and_private

### O3: Release, Reassignment, and Retained History

- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_offline_lifecycle_and_reassignment_isolate_history
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_removed_takeover_modes_and_external_target_preservation
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_released_member_can_reconcile_lost_leave_response
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_stale_member_release_cannot_release_new_registration
- [tests/unit/mailbox/test_managed.py](../../../../tests/unit/mailbox/test_managed.py)::test_deregister_mailbox_purge_preserves_canonical_history_and_symlink_targets

### O4: Registry Selection and Presence Independence

- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_separate_registries_reuse_an_address_without_cross_delivery
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_lifecycle_cleanup_preserves_durable_remote_membership
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_registry_association_is_explicit_and_never_rewritten
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_repair_preserves_member_verifiers_and_rejects_missing_authority

### O5: Narrow Service and Private Diagnostics

- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_narrow_route_inventory_and_redacted_validation
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_plaintext_remote_credentials_are_rejected
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_non_loopback_listener_requires_explicit_https_termination
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_private_configuration_error_does_not_echo_embedded_url_credentials
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_remote_backend_contains_connection_failure_and_preserves_scope_conflict

### O6: Managed Attachment Transfers

- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_managed_attachments_require_upload_and_message_ownership
- [tests/integration/mailbox/test_offline_registry_process.py](../../../../tests/integration/mailbox/test_offline_registry_process.py)::test_remote_members_survive_restart_and_reassignment_with_attachment_isolation

### O7: Remote Process and Running Body Integration

- [tests/integration/mailbox/test_offline_registry_process.py](../../../../tests/integration/mailbox/test_offline_registry_process.py)::test_remote_members_survive_restart_and_reassignment_with_attachment_isolation
- [tests/integration/mailbox/test_offline_registry_process.py](../../../../tests/integration/mailbox/test_offline_registry_process.py)::test_runtime_remote_join_preserves_body_and_reconciles_publication

### O8: Local Late Registration and Body Continuity

- [tests/unit/agents/realm_controller/test_runtime_mailbox.py](../../../../tests/unit/agents/realm_controller/test_runtime_mailbox.py)::test_register_filesystem_mailbox_updates_headless_launch_plan_and_manifest
- [tests/unit/agents/realm_controller/test_runtime_mailbox.py](../../../../tests/unit/agents/realm_controller/test_runtime_mailbox.py)::test_register_filesystem_mailbox_marks_local_interactive_session_active
- [tests/unit/agents/realm_controller/test_runtime_mailbox.py](../../../../tests/unit/agents/realm_controller/test_runtime_mailbox.py)::test_late_mailbox_registration_supports_joined_sessions_without_relaunch_posture
- [tests/unit/agents/realm_controller/test_runtime_mailbox.py](../../../../tests/unit/agents/realm_controller/test_runtime_mailbox.py)::test_late_mailbox_unregistration_supports_joined_sessions_without_relaunch_posture
- [tests/unit/agents/realm_controller/test_runtime_mailbox.py](../../../../tests/unit/agents/realm_controller/test_runtime_mailbox.py)::test_retry_leave_after_reassignment_preserves_the_next_owner

### G1: Scoped References and Pre-I/O Rejection

- [tests/unit/mailbox/test_scope.py](../../../../tests/unit/mailbox/test_scope.py)::test_reference_cannot_cross_scope
- [tests/unit/mailbox/test_scope.py](../../../../tests/unit/mailbox/test_scope.py)::test_released_address_does_not_expose_replacement_to_old_service
- [tests/unit/mailbox/test_scope.py](../../../../tests/unit/mailbox/test_scope.py)::test_wrong_reference_is_rejected_before_read_mutation
- [tests/unit/agents/realm_controller/test_gateway_dual_mail.py](../../../../tests/unit/agents/realm_controller/test_gateway_dual_mail.py)::test_fresh_send_conflict_has_no_backend_side_effects

### G2: Dual Summary and Explicit Channel Admission

- [tests/unit/agents/realm_controller/test_gateway_dual_mail.py](../../../../tests/unit/agents/realm_controller/test_gateway_dual_mail.py)::test_empty_summary_and_explicit_channel_binding_admission
- [tests/unit/agents/realm_controller/test_gateway_dual_mail.py](../../../../tests/unit/agents/realm_controller/test_gateway_dual_mail.py)::test_online_outage_preserves_canonical_identity_and_offline_operations
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_routes_reject_non_loopback_listener
- [tests/unit/agents/realm_controller/test_gateway_dual_mail.py](../../../../tests/unit/agents/realm_controller/test_gateway_dual_mail.py)::test_mail_network_io_does_not_hold_terminal_control_lock

### G3: Shared Mailbox Lifecycle

- [tests/integration/agents/realm_controller/test_gateway_runtime_contract.py](../../../../tests/integration/agents/realm_controller/test_gateway_runtime_contract.py)::test_gateway_http_mail_read_route_marks_message_read_through_live_gateway
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_routes_support_filesystem_mailbox_without_runtime_roundtrip
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_read_route_marks_filesystem_message_read_without_queue_mutation
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_routes_support_stalwart_mailbox_with_mocked_jmap
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_explicit_no_reply_operator_post_rejects_reply
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_offline_lifecycle_and_reassignment_isolate_history

### N1: Notifier Controls and Manifest Authority

- [tests/integration/agents/realm_controller/test_gateway_runtime_contract.py](../../../../tests/integration/agents/realm_controller/test_gateway_runtime_contract.py)::test_gateway_http_mail_notifier_routes_follow_manifest_mailbox_contract
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_rejects_enablement_without_manifest_mailbox_binding
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_rejects_enablement_when_manifest_is_missing
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_supports_manifest_backed_mailbox_without_tmux_projection
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_appendix_status_update_and_delete_semantics
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_gateway_mail_notifier_commands_allow_joined_session_without_relaunch_posture

### N2: Independent Periodic Reminders and Admission

- [tests/integration/agents/realm_controller/test_gateway_runtime_contract.py](../../../../tests/integration/agents/realm_controller/test_gateway_runtime_contract.py)::test_gateway_runtime_mail_notifier_repeats_when_prompt_ready_returns
- [tests/integration/agents/realm_controller/test_gateway_runtime_contract.py](../../../../tests/integration/agents/realm_controller/test_gateway_runtime_contract.py)::test_gateway_http_mail_notifier_persists_queryable_audit_rows
- [tests/unit/agents/realm_controller/test_gateway_dual_mail.py](../../../../tests/unit/agents/realm_controller/test_gateway_dual_mail.py)::test_channels_keep_independent_configuration_and_periodic_reminders
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_polls_mailbox_local_state_and_repeats_after_restart
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_stalwart_adapter_defers_then_repeats_for_unchanged_unread_mail
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_defers_while_busy_and_logs_the_skip
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_defers_when_claude_tracked_surface_reports_draft

### N3: One-Shot Compaction Continuity

- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_pre_notification_compaction_does_not_repeat_for_unchanged_mail
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_pre_notification_compaction_runs_once_for_expanded_mail_set
- [tests/unit/agents/realm_controller/test_gateway_dual_mail.py](../../../../tests/unit/agents/realm_controller/test_gateway_dual_mail.py)::test_online_canonical_change_preserves_offline_compaction_eligibility

### S1: Current Resolver and Installed Static Skills

- [tests/unit/agents/test_mailbox_runtime_support.py](../../../../tests/unit/agents/test_mailbox_runtime_support.py)::test_resolve_live_mailbox_binding_from_manifest_path_uses_manifest_binding_and_current_instance_gateway
- [tests/unit/agents/test_mailbox_runtime_support.py](../../../../tests/unit/agents/test_mailbox_runtime_support.py)::test_install_runtime_mailbox_system_skills_for_tool_projects_gateway_and_transport_docs
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_mail_resolve_live_local_returns_normalized_payload
- [tests/integration/agents/realm_controller/test_mailbox_runtime_contract.py](../../../../tests/integration/agents/realm_controller/test_mailbox_runtime_contract.py)::test_resolve_live_cli_surfaces_attached_gateway_base_url_for_mailbox_work

### S2: Notifier Prompt Routing and API Fallback

- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_renders_gateway_bootstrap_prompt_with_houmao_gateway_skill
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_renders_tool_native_skill_invocation
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_notifier_falls_back_when_required_skill_is_missing

### P1: Passive Summary and Lifecycle Forwarding

- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailStatusEndpoint::test_returns_200_with_mocked_client
- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailStatusEndpoint::test_no_gateway_returns_502
- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailListEndpoint::test_returns_200_with_mocked_client
- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailSendEndpoint::test_returns_200_with_mocked_client
- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailPostEndpoint::test_returns_200_with_mocked_client
- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailReplyEndpoint::test_returns_200_with_mocked_client

### P2: Complete Proxy Set and Structured Conflicts

- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::test_complete_channel_mail_proxy_preserves_online_targeting
- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::test_mail_proxy_preserves_structured_scope_conflict_without_channel_retry

### P3: One Notifier Authority Through Proxy

- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailNotifierEndpoint::test_status_returns_200_with_mocked_client
- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailNotifierEndpoint::test_enable_returns_200_with_mocked_client
- [tests/unit/passive_server/test_app_contracts.py](../../../../tests/unit/passive_server/test_app_contracts.py)::TestGatewayMailNotifierEndpoint::test_disable_returns_200_with_mocked_client
- [tests/unit/passive_server/test_service.py](../../../../tests/unit/passive_server/test_service.py)::TestGatewayMailNotifier::test_enable_success_returns_status
- [tests/unit/server/test_app_contracts.py](../../../../tests/unit/server/test_app_contracts.py)::test_managed_agent_routes_delegate_to_service_methods

### C1: CLI Self/Single Authority

- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_resolve_managed_agent_mail_target_uses_current_session_metadata
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_resolve_managed_agent_mail_target_prefers_explicit_selector
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_resolve_managed_agent_mail_target_fails_outside_tmux_without_selectors
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_mail_resolve_live_server_returns_pair_authority_payload

### C2: Verified Actions and Submission-Only Fallback

- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_mail_send_local_headless_uses_verified_manager_direct_result
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_mail_archive_local_headless_uses_verified_manager_direct_result
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_mail_send_local_tui_without_gateway_returns_submission_only_result
- [tests/unit/srv_ctrl/test_commands.py](../../../../tests/unit/srv_ctrl/test_commands.py)::test_agents_mail_post_forwards_reply_policy_default_and_explicit_none

### C3: Native Notifier Arguments

- [tests/unit/srv_ctrl/test_commands.py](../../../../tests/unit/srv_ctrl/test_commands.py)::test_agents_gateway_mail_notifier_enable_current_session_forwards_interval_and_mode
- [tests/unit/srv_ctrl/test_commands.py](../../../../tests/unit/srv_ctrl/test_commands.py)::test_agents_gateway_mail_notifier_enable_rejects_invalid_mode
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_gateway_mail_notifier_commands_use_passive_pair_client

### C4: Scoped Membership Command Shape

- [tests/unit/srv_ctrl/test_commands.py](../../../../tests/unit/srv_ctrl/test_commands.py)::test_agents_mailbox_help_mentions_late_registration_surface
- [tests/unit/srv_ctrl/test_commands.py](../../../../tests/unit/srv_ctrl/test_commands.py)::test_agents_mailbox_join_has_no_overwrite_confirmation_inputs
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_register_mailbox_binding_uses_exclusive_claim_without_overwrite_options
- [tests/unit/srv_ctrl/test_managed_agents.py](../../../../tests/unit/srv_ctrl/test_managed_agents.py)::test_late_mailbox_commands_reject_server_backed_targets

### C5: Administrative Ownership and Maintenance Selection

- [tests/unit/srv_ctrl/test_mailbox_commands.py](../../../../tests/unit/srv_ctrl/test_mailbox_commands.py)::test_mailbox_register_rejects_conflict_even_with_interactive_yes
- [tests/unit/srv_ctrl/test_mailbox_commands.py](../../../../tests/unit/srv_ctrl/test_mailbox_commands.py)::test_mailbox_register_rejects_removed_yes_flag
- [tests/unit/srv_ctrl/test_mailbox_commands.py](../../../../tests/unit/srv_ctrl/test_mailbox_commands.py)::test_project_mailbox_register_rejects_interactive_takeover
- [tests/unit/srv_ctrl/test_mailbox_commands.py](../../../../tests/unit/srv_ctrl/test_mailbox_commands.py)::test_project_mailbox_register_rejects_removed_yes_flag
- [tests/unit/srv_ctrl/test_mailbox_commands.py](../../../../tests/unit/srv_ctrl/test_mailbox_commands.py)::test_mailbox_accounts_commands_and_project_wrapper_have_root_parity

### G4: Recipient Preflight and Forged Storage Handles

- [tests/unit/srv_ctrl/commands/test_mail_channel_commands.py](../../../../tests/unit/srv_ctrl/commands/test_mail_channel_commands.py)::test_online_mixed_address_and_foreign_scope_batch_never_reaches_provider
- [tests/unit/srv_ctrl/commands/test_mail_channel_commands.py](../../../../tests/unit/srv_ctrl/commands/test_mail_channel_commands.py)::test_offline_mixed_recipient_batch_fails_before_staging_or_delivery
- [tests/unit/srv_ctrl/commands/test_mail_channel_commands.py](../../../../tests/unit/srv_ctrl/commands/test_mail_channel_commands.py)::test_forged_foreign_storage_id_cannot_reply_or_partially_mark_owned_batch

### N4: Concurrent Notifier Configuration Reads

- [tests/unit/agents/realm_controller/test_notifier_scope_storage.py](../../../../tests/unit/agents/realm_controller/test_notifier_scope_storage.py)::test_empty_status_read_cannot_overwrite_concurrent_enable

### F1: Canonical Principal and Historical Content

- [tests/unit/mailbox/test_protocol.py](../../../../tests/unit/mailbox/test_protocol.py)::test_canonical_message_serialization_round_trips
- [tests/unit/mailbox/test_managed.py](../../../../tests/unit/mailbox/test_managed.py)::test_deliver_message_routes_by_address_and_state_updates_use_active_registration
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_routes_support_stalwart_mailbox_with_mocked_jmap

### F2: Current Format and Explicit Legacy Rejection

- [tests/unit/mailbox/test_protocol_notify_fields.py](../../../../tests/unit/mailbox/test_protocol_notify_fields.py)::test_protocol_version_is_four
- [tests/unit/mailbox/test_protocol_notify_fields.py](../../../../tests/unit/mailbox/test_protocol_notify_fields.py)::test_legacy_v1_envelope_is_rejected_at_validation
- [tests/unit/mailbox/test_protocol_notify_fields.py](../../../../tests/unit/mailbox/test_protocol_notify_fields.py)::test_v2_envelope_is_rejected_at_validation
- [tests/unit/mailbox/test_protocol_notify_fields.py](../../../../tests/unit/mailbox/test_protocol_notify_fields.py)::test_current_envelope_without_notify_fields_remains_valid
- [tests/unit/mailbox/test_filesystem.py](../../../../tests/unit/mailbox/test_filesystem.py)::test_bootstrap_rejects_unsupported_protocol_version
- [tests/unit/mailbox/test_filesystem.py](../../../../tests/unit/mailbox/test_filesystem.py)::test_bootstrap_rejects_stale_principal_scoped_mailbox_root

### F3: Registration Helpers, Symlinks, and Authority-Preserving Repair

- [tests/unit/mailbox/test_managed.py](../../../../tests/unit/mailbox/test_managed.py)::test_register_mailbox_script_validation_failure_emits_one_json_error_without_mutation
- [tests/unit/mailbox/test_managed.py](../../../../tests/unit/mailbox/test_managed.py)::test_register_mailbox_safe_symlink_reuses_same_target_registration
- [tests/unit/mailbox/test_managed.py](../../../../tests/unit/mailbox/test_managed.py)::test_register_mailbox_safe_symlink_preserves_existing_private_mailbox_state
- [tests/unit/mailbox/test_managed.py](../../../../tests/unit/mailbox/test_managed.py)::test_explicit_release_preserves_history_before_reassignment
- [tests/unit/mailbox/test_managed.py](../../../../tests/unit/mailbox/test_managed.py)::test_repair_mailbox_index_rebuilds_address_based_projections_and_state
- [tests/unit/mailbox/test_offline_registry.py](../../../../tests/unit/mailbox/test_offline_registry.py)::test_repair_preserves_member_verifiers_and_rejects_missing_authority

### F4: Gateway Routes, Diagnostics, and Notifier Audit

- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_diagnostics_capture_http_validation_without_raw_body
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_diagnostics_capture_mailbox_success_failure_and_repair_hint
- [tests/unit/agents/realm_controller/test_gateway_support.py](../../../../tests/unit/agents/realm_controller/test_gateway_support.py)::test_gateway_mail_reply_enabled_operator_post_routes_reply_to_reserved_operator_mailbox
- [tests/integration/agents/realm_controller/test_gateway_runtime_contract.py](../../../../tests/integration/agents/realm_controller/test_gateway_runtime_contract.py)

### F5: Scoped CLI Errors, Content Options, and Structural Inspection

- [tests/unit/srv_ctrl/test_commands.py](../../../../tests/unit/srv_ctrl/test_commands.py)::test_main_renders_mailbox_click_exception_without_traceback
- [tests/unit/srv_ctrl/test_commands.py](../../../../tests/unit/srv_ctrl/test_commands.py)::test_agents_mail_post_help_reports_operator_mailbox_default
- [tests/unit/srv_ctrl/test_commands.py](../../../../tests/unit/srv_ctrl/test_commands.py)::test_agents_mail_post_forwards_reply_policy_default_and_explicit_none
- [tests/unit/srv_ctrl/test_mailbox_commands.py](../../../../tests/unit/srv_ctrl/test_mailbox_commands.py)::test_mailbox_messages_commands_and_project_wrapper_share_visibility
- [tests/unit/srv_ctrl/test_agents_mail_notify_block.py](../../../../tests/unit/srv_ctrl/test_agents_mail_notify_block.py)

## Requirement and Scenario Inventory

### agent-discovery-registry

[Spec delta](specs/agent-discovery-registry/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Shared registry records are strict, secret-free contracts that point to runtime-owned state | Registry record publishes runtime pointers without copying runtime payloads<br>Detached session omits live gateway connect metadata<br>Refresh keeps the same generation for the same live session | I3, B4 |
| Shared-registry records persist authoritative agent identity rather than registry-specific agent keys | Initial authoritative agent id is derived from the HOUMAO canonical name<br>Default UUID is the registry key | I1, I2, I3 |
| Durable mail membership is separate from local runtime presence | Live cleanup preserves offline address ownership<br>Remote member has no registry-host manifest path | O4, O7 |
| Canonical mail summaries are projections of binding authority | Provider outage leaves canonical summary unchanged<br>Projection update fails after a binding change | B4, G2 |

### agent-gateway

[Spec delta](specs/agent-gateway/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Shared gateway mailbox facade exposes lifecycle routes | Peek does not mutate read state through the gateway<br>Read mutates read state through the gateway<br>Archive shortcut remains available<br>Channel omission does not use canonical precedence<br>Empty status remains readable<br>A new send pins its intended mailbox | G1, G2, G3 |
| Gateway reply marks the parent message answered | Gateway reply acknowledges without closing the mail | G3, O3 |
| Gateway diagnostic logs capture HTTP and mailbox failure evidence without raw sensitive content | Malformed mailbox send request is captured<br>Mailbox delivery failure records repair context safely | F4 |
| The gateway exposes a structured HTTP API on the resolved listener address | Reminder registration uses the live gateway HTTP surface<br>Send-keys reminder request is validated through the reminder route family<br>Unknown reminder identifier fails explicitly | G2, G3, N1, F4 |
| Gateway notifier records structured per-poll decision auditing for later review | Busy poll records an explicit skip decision<br>Enqueue poll records the created reminder request<br>Durable audit history remains the detailed inspection surface | F4, N1, N2 |
| Gateway operator-origin post defaults to operator mailbox replies | Direct gateway post omitted policy creates a reply-enabled message<br>Direct gateway explicit no-reply policy is honored<br>Pair-managed proxy preserves gateway post default | G3, F4 |

### agent-gateway-mail-notifier

[Spec delta](specs/agent-gateway-mail-notifier/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Gateway mail notifier can be configured through dedicated HTTP control routes | Mail notifier is enabled with an explicit interval<br>Mail notifier can be disabled explicitly<br>Mail notifier enablement fails for a session without mailbox support<br>Mail notifier enablement fails when manifest-backed capability discovery is unavailable<br>Tmux-backed late registration becomes notifier-ready after durable binding validation<br>Joined tmux session without relaunch posture becomes notifier-ready after late registration<br>Durable mailbox presence without actionable validation rejects notifier enablement<br>Omitted appendix preserves stored notifier appendix<br>Provided appendix replaces stored notifier appendix<br>Empty appendix clears stored notifier appendix<br>Disable preserves notifier appendix state | N1, N4 |
| Server-managed notifier control projects the same gateway-owned notifier state | Enabling notifier through the server route is visible through the direct gateway route<br>Disabling notifier through the direct gateway route is visible through the server route | N1, P3 |
| Gateway mail notifier supports notification modes | Omitted mode enables any-inbox notification<br>Any-inbox mode notifies for read answered inbox mail<br>Unread-only mode ignores read inbox mail<br>Unread-only mode notifies for unread inbox mail<br>Archived mail is not notifier-eligible in either mode | N1, N2, C3 |
| Both mail channels preserve periodic reminder semantics | Unchanged mail generates later reminders<br>Simultaneous channel reminders respect body admission | N2 |
| Notifier channel and compaction state remain independent | Online attachment does not reset offline compaction history | N3, S2 |

### agent-identity

[Spec delta](specs/agent-identity/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Agent IDs are immutable globally unique logical identities | Same ID is observed from another host<br>Identity survives operational changes | I1, I2, I3, O2 |
| New agents use UUID generation unless explicitly configured otherwise | UUID is the creation default<br>Caller opts into name-derived identity<br>Supplied hash-like IDs remain valid identities | I1, I2 |
| Identity selection occurs only at creation boundaries | Manifest persistence does not generate another UUID<br>Missing durable identity is explicit | I2, B2, I3 |

### agent-mailbox-bindings

[Spec delta](specs/agent-mailbox-bindings/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Agents have two independent optional mail bindings | Both bindings coexist<br>Mailbox-disabled agent remains valid<br>Multiple accounts in one channel are rejected | B1, B3 |
| Canonical mail identity follows configured online-first precedence | Online identity takes precedence without removing offline ownership<br>Explicit online removal falls back to offline identity<br>Outage does not rename the agent | B1, G2, O3 |
| Binding identity is distinct from configuration revision | Credential changes preserve account scope<br>Detached binding cannot be resurrected by an old writer | B2 |
| Runtime binding mutation is atomic and revision-checked | Slow controller persistence preserves a new binding<br>Two binding updates race | B2, B4 |
| Mail references are scoped to their owner and binding | Online reference cannot target offline mail<br>Account replacement invalidates old targeting | G1 |
| Operational status separates binding presence from health | Online failure leaves offline mail available | B4, G2 |
| Provider selection does not redefine the mail contract | Launch-time Stalwart and offline mail are configured together<br>Unsupported provider operation is visible | B3, G3 |

### agent-mailbox-protocol

[Spec delta](specs/agent-mailbox-protocol/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Principal-based mailbox addressing | Agent mailbox uses canonical agent identity<br>Human mailbox uses the same principal model | B3, F1 |
| Mail operations select an explicit isolated channel | Online-first identity does not redirect offline mail<br>Online recipient has only an offline binding<br>Cross-channel batch is rejected before side effects | G1, G2, G3, G4 |
| Replies and lifecycle operations preserve message scope | Preferred address changes during an offline conversation<br>Reference belongs to another binding | G1, G3, G4, O3, B1 |
| Current mailbox format uses version 4 | Newly composed canonical envelope advertises protocol version 4<br>Current envelope without notify fields remains valid<br>Legacy canonical envelopes are rejected<br>Canonical envelopes advertising the wrong protocol version are rejected | F2 |
| Removed: Mailbox protocol version reflects the notify-aware canonical envelope | Removed contract; use the replacement requirements. | F2 |

### agent-mailbox-registration-lifecycle

[Spec delta](specs/agent-mailbox-registration-lifecycle/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Filesystem mailbox delivery routes through active mailbox registrations keyed by full address | Delivery resolves recipient through active mailbox address<br>Delivery fails when no active mailbox registration exists for an address<br>Purge preserves canonical recipient history | F1, O3, O7 |
| Filesystem mailbox leave and deregistration have defined cleanup semantics | Deactivate stops future delivery and preserves historical state<br>Purge removes registration-scoped state without deleting canonical messages<br>Symlink deregistration does not delete the external target directory by default<br>New owner does not inherit the old inbox | O3 |
| Symlink-backed filesystem registrations validate and safely prepare explicit private mailbox directories | Safe symlink registration reuses a matching existing mailbox binding<br>Safe symlink registration rejects a concrete mailbox directory inside the shared root<br>Safe symlink registration fails when the address slot is occupied by a different artifact<br>Safe symlink registration rejects reuse of one private mailbox directory by a different active address<br>Safe symlink registration prepares an existing non-empty mailbox directory non-destructively<br>Released symlink registration is not reactivated | F3, O1, O3 |
| Filesystem mailbox lifecycle operations are published as managed mailbox helpers with structured JSON contracts | Managed lifecycle helpers are materialized with the mailbox rules asset set<br>Register helper uses a structured JSON payload and result<br>Deregister helper uses a structured JSON payload and result<br>Runtime bootstrap applies safe registration semantics | F3, C4, C5 |
| Removed: Filesystem mailbox join uses explicit conflict-resolution modes | Removed contract; use the replacement requirements. | C4, C5, O3 |
| Removed: Refactored filesystem mailbox roots are hard-reset only within the intended v1 contract | Removed contract; use the replacement requirements. | F2 |
| Removed: Filesystem mailbox operations serialize on address-scoped locks | Removed contract; use the replacement requirements. | O1, O3, F3 |
| Offline join rejects occupied address takeover | Safe join reuses an existing matching registration<br>Safe join fails on real identity or path conflict<br>Force join cannot take an occupied address<br>Stash join cannot take an occupied address | O1, O2, O3 |
| Filesystem mailbox roots require the current ownership-aware format | Bootstrap rejects a stale principal-keyed or earlier-format mailbox root | F2 |
| Filesystem mailbox operations serialize ownership and delivery on address-scoped locks | Delivery and explicit release serialize on the same address lock<br>Multi-address delivery acquires locks deterministically | O1, O3, F3 |

### agent-mailbox-system-skills

[Spec delta](specs/agent-mailbox-system-skills/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Mailbox system skills use a stable resolver contract for current mailbox discovery | Filesystem mailbox skill resolves current mailbox state through the manager-owned resolver<br>Stalwart mailbox skill resolves current mailbox state through the manager-owned resolver | S1, B4 |
| Tmux-backed mailbox system skills resolve current mailbox bindings through a runtime-owned live resolver | Filesystem mailbox skill observes late-registered binding without provider relaunch<br>Attached mailbox skill resolves the live gateway mail facade through `houmao-mgr agents mail`<br>Stalwart no-gateway mailbox work uses the live resolver instead of stale process env | S1, S2 |
| Runtime-owned mailbox skill guidance keeps tmux integration behind the runtime-owned helper boundary | Filesystem mailbox skill does not ask the agent to scrape tmux state or call a Python module directly | S1 |
| Projected mailbox system skills keep routine attached-session actions on the shared gateway facade | Attached mailbox session uses the shared gateway facade when available<br>Mailbox session without gateway falls back to `houmao-mgr agents mail`<br>Non-authoritative manager fallback result triggers explicit verification<br>Thin shell helpers stay wrappers over supported surfaces | S1, C2 |
| Unified ordinary-mailbox skill uses the manager-owned live resolver as the ordinary gateway discovery contract | Unified ordinary-mailbox skill obtains the current endpoint from prompt context when available<br>Unified ordinary-mailbox skill falls back to `houmao-mgr agents mail resolve-live`<br>Unified ordinary-mailbox skill avoids `pixi` and direct Python-module resolver guidance | S1, S2 |
| Mailbox skill workflows select channels explicitly | Dual-mail agent processes an offline reminder<br>Round lacks channel context | S2, G1, G2 |
| Mailbox skill installation is independent of late binding health | Already-running mailbox-disabled body gains offline mail | S2, O8 |

### houmao-mgr-mailbox-cli

[Spec delta](specs/houmao-mgr-mailbox-cli/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Removed: `houmao-mgr mailbox register` and `unregister` expose operator mailbox lifecycle control | Removed contract; use the replacement requirements. | C5 |
| Administrative offline registration enforces registry ownership | Free address is registered safely<br>Administrative register cannot overwrite another agent<br>Administrative release retains canonical history | C5, O1, O3 |
| Mailbox maintenance root selection does not change registry authority | Project default differs from configured registry store | O4, C5 |
| `houmao-mgr mailbox init` bootstraps or validates one filesystem mailbox root | Init without overrides uses the active overlay mailbox root<br>Init cannot silently replace an existing registry store association | O4, C5 |
| `houmao-mgr mailbox repair` rebuilds filesystem mailbox index state locally | Operator repairs a mailbox root locally<br>Repair preserves membership authority<br>Lost ownership index is not reconstructed from address paths | O4, F3 |

### houmao-mgr-project-mailbox-cli

[Spec delta](specs/houmao-mgr-project-mailbox-cli/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Removed: `project mailbox register` mirrors the generic mailbox overwrite-confirmation contract | Removed contract; use the replacement requirements. | C5 |
| Project mailbox registration preserves registry ownership rules | Project registration conflicts with an existing owner<br>Project root belongs to the configured registry | C5, O4 |
| `houmao-mgr project mailbox messages` is structural inspection, not participant-local state reporting | Project mailbox message list omits participant-local mutable state<br>Project mailbox message get omits participant-local mutable state<br>Project mailbox verification guidance points operators to actor-scoped mail state | F5, C2 |

### houmao-srv-ctrl-native-cli

[Spec delta](specs/houmao-srv-ctrl-native-cli/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| `houmao-mgr agents mail` exposes pair-native mailbox follow-up commands | Same-session resolve-live succeeds without explicit selectors<br>Explicit selector wins over same-session discovery<br>Outside-tmux mail discovery fails without explicit selectors<br>Local mail list uses manager-owned direct mailbox execution<br>Local live-TUI send without verified direct authority returns submission-only fallback<br>Local live-TUI post without verified authority fails explicitly<br>Pair-managed target still uses pair-owned mail authority | C1, C2, S1 |
| `houmao-mgr agents mail` exposes mailbox lifecycle commands | Operator archives selected mail from the CLI<br>CLI peek does not mark a message read<br>CLI read marks a message read | C2, G3 |
| Native gateway mail-notifier CLI configures notification mode | CLI enable defaults to any-inbox mode<br>CLI enable accepts unread-only mode<br>CLI rejects invalid notifier mode<br>CLI omits appendix field when not provided<br>CLI forwards non-empty appendix text<br>CLI forwards empty appendix text to clear appendix | C3, N1 |
| `houmao-mgr agents mailbox` exposes local late mailbox registration commands | Operator inspects late registration commands<br>Remote registry join keeps the body running<br>Operator uses a native late mailbox registration path under `agents` | C4, O7, O8 |
| `houmao-mgr` renders expected mailbox-related operator failures without Python tracebacks | Joined mailbox registration failure renders as a clean CLI error<br>Gateway mail-notifier enable failure renders as a clean CLI error | F5 |
| Server-backed gateway raw control and notifier commands accept passive server pair authorities | Gateway raw control input works through a passive server<br>Gateway mail notifier control works through a passive server | C3, P3, F5 |
| `houmao-mgr mailbox messages` reports structural mailbox message inspection | Root mailbox message list omits participant-local view-state flags<br>Root mailbox message get omits participant-local view-state flags | F5, C2 |
| `houmao-mgr agents mail post` defaults to operator mailbox replies | Omitted CLI reply policy creates a reply-enabled operator-origin post<br>Explicit CLI no-reply policy remains supported<br>CLI help reflects the new default | C2, F5 |
| `houmao-mgr agents mail send` and `post` accept `--notify-block` and respect the houmao-notify body fence | Operator supplies an explicit notify-block on send with default placement<br>Operator supplies notify-block with prepend placement on post<br>Operator authors notify content via body fence on post<br>Oversize notify-block surfaces a clean CLI error rather than a traceback<br>Unsupported notify-auth scheme surfaces a clean CLI error | F5 |
| Native agent creation exposes explicit identity generation modes | Default creation names do not determine IDs<br>Caller requests name-hash mode<br>Conflicting ID inputs fail before creation | I1, I2 |

### managed-agent-mailbox-registration

[Spec delta](specs/managed-agent-mailbox-registration/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Removed: `houmao-mgr agents mailbox` exposes late mailbox registration for local managed agents | Removed contract; use the replacement requirements. | C4 |
| Removed: `houmao-mgr agents mailbox register` creates shared registration and persists session mailbox binding | Removed contract; use the replacement requirements. | C4, O1 |
| Removed: Late mailbox registration reports activation state by runtime posture | Removed contract; use the replacement requirements. | C4, O8 |
| Removed: `houmao-mgr agents mailbox unregister` removes the session binding and unregisters the address | Removed contract; use the replacement requirements. | C4, O3 |
| Removed: `houmao-mgr agents mailbox status` reports late mailbox registration posture | Removed contract; use the replacement requirements. | C4, G2 |
| Scoped offline membership commands support existing local agent bodies | Offline-disabled body joins a remote registry<br>Joined tmux body needs no relaunch posture | O7, O8, C4 |
| Offline join and leave publish confirmed ownership outcomes | Address conflict does not mutate runtime bindings<br>Registry committed but the local response was lost<br>Offline leave preserves online identity | O2, O3, O7, B4 |
| Offline status distinguishes registration from connectivity | Registry outage leaves membership visible | G2, O5, O7 |

### offline-mail-registry

[Spec delta](specs/offline-mail-registry/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Registry selection provides offline mail scope | Separate registries may use the same address<br>Remote agent joins without a cluster identifier | O4, O7 |
| Offline address ownership is exclusive and atomic | Conflicting agent cannot join<br>Concurrent claims have one winner<br>Owner retries registration | O1, O2 |
| Membership outlives runtime presence | Stopped recipient receives offline mail<br>Registry host cannot probe remote tmux | O4, O7 |
| Offline release is explicit and preserves ownership history | Online attachment preserves offline membership<br>Released address is reassigned safely | O3, O7 |
| Registry-host APIs authorize agent-scoped mail access | Agent ID is not an access credential<br>Authenticated sender cannot impersonate another member | O2, O5 |
| Local and remote access use the same offline mail semantics | Remote reply preserves offline ancestry<br>Remote archive updates authoritative state | O3, O7, G3 |
| Remote attachment access is independent of host-local paths | Sender path is not available on registry host | O6 |
| Communication membership grants no remote lifecycle ownership | Member attempts remote body control | O5 |
| Registry restart restores membership and mail authority | Registry restarts while agents remain remote | O2, O7 |

### passive-server-gateway-proxy

[Spec delta](specs/passive-server-gateway-proxy/spec.md)

| Requirement | Named Scenarios | Evidence |
| --- | --- | --- |
| Passive server provides a mail status proxy endpoint | Mail status returns the gateway's mailbox status<br>Mail status returns 502 when no gateway is attached | P1, G2 |
| Passive server provides a mail list proxy endpoint | Mail list forwards to the gateway and returns messages | P1 |
| Passive server provides a mail send proxy endpoint | Mail send forwards to the gateway and returns the action response | P1 |
| Passive server provides a mail post proxy endpoint | Mail post forwards to the gateway and returns the action response | P1 |
| Passive server provides a mail reply proxy endpoint | Mail reply forwards to the gateway and returns the action response | P1 |
| Passive server provides gateway mail-notifier proxy endpoints | Mail-notifier status returns the live gateway notifier payload<br>Mail-notifier enable forwards through the passive proxy<br>Mail-notifier disable returns 502 when no gateway is attached<br>Mail-notifier status includes live appendix text<br>Passive proxy forwards non-empty appendix text unchanged<br>Passive proxy forwards empty appendix text unchanged | P3 |
| Gateway mail-notifier proxy preserves notification mode | Proxy enable forwards explicit mode<br>Proxy status returns notifier mode | P3 |
| Channel-selected lifecycle proxies cover the complete shared operation set | Wrong-channel reference remains an error<br>Registry inbox is available without a body gateway | P2, O7 |

## Remaining Stalwart Work and Successor Gate

Change 01 establishes identity, two slot envelopes, revision authority, registry-hosted offline mail, channel-scoped facades, and per-channel notifier state. It does not complete GitHub #79 or #80.

The current Stalwart list/poll path still has the existing full-inbox/body-fetch costs, per-message role lookup costs, and repeated session/account discovery costs. There is no completed bounded incremental observation checkpoint, bounded eligibility cache, or live externally provisioned attachment lifecycle in this foundation. Change 02 must replace these paths with server-filtered metadata pages, reusable connection epochs, bounded Email/changes reconciliation, stale-state recovery, and revision-safe online attachment/refresh/detach.

Periodic unchanged-work reminders, explicit archive completion, readiness/pending-input admission, and one-shot compaction continuity are acceptance constraints for the successor. Bounded metadata caching must not redefine completion or reset compaction history.

Implement, verify, and synchronize change 01 before applying `mail-02-attach-online-mail-and-sync-stalwart`. Neither a complete planning status nor this map authorizes skipping that gate. Archive and GitHub issue closure remain separate requested workflows. No 100-agent/million-message capacity result is claimed here.
