# Execution Context Acceptance Evidence

This map covers the 23 requirement blocks and 51 scenarios in `openspec/changes/add-execution-owner-aware-control/specs/`. It separates real host/native qualification from component and reused-runtime coverage. Docker transport implementation is included; the user explicitly deferred live Docker qualification on 2026-11-17. No row claims a real Docker launch succeeded.

## Executed Qualification

| Evidence | Executed Selection | Result |
| --- | --- | --- |
| OS fixtures and real helper admission | `test_fixture_boundaries.py` and `test_owner_stdio.py`, restricted temporary operator/owner accounts and fixture-owned SSH daemon | 7 passed in 9.05 seconds |
| Native DSH ACP through sudo and Web through SSH | `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner[headless-sudo]` and `[tui-ssh]`, standard maintained helper with diagnostics disabled | 2 passed in 123.73 seconds |
| Native Codex through sudo | `CX::test_actual_codex_headless_owner_routing`, Codex CLI 0.162.1 | 1 passed in 20.25 seconds |
| Docker | Native argv, immutable container-ID profile contract, and no-fallback component tests | Live qualification deferred by user instruction |

Both DSH cases use the maintained `scripts/agents/test-fixtures/fixture.py` workflow with `--case cloud-api --client dsh --model controlled --prompt-mode unattended`, context window 8192, maximum output 128, and reasoning disabled. A deliberately selected external env file supplies synthetic credentials and a local controlled Messages endpoint. DSH is the qualified 0.2.2-rc.3 executable. Each case launches two real agents under one owner/profile with distinct generated Ed25519 credential references and native-home key copies. The test checks different stable key digests, unchanged sibling generation, actual manifest UID/GID, target-only project access, targeted stop, and preservation of the operator's identically named session.

The Codex smoke uses `--case self-hosted --client codex --model controlled --mode headless --prompt-mode unattended` through the same fixture workflow. Its explicit external env file contains a synthetic key and a local Responses endpoint. The SSE fixture follows the primary reference at `extern/orphan/codex/codex-rs/core/tests/common/responses.rs`. The test verifies a real delegated launch, qualified CODEX_HOME, manifest UID/GID, captured native prompt input, successful finalized turn, and stop. It does not qualify Codex hot refresh, SSH execution, or container execution.

Reproduce the native selections with explicit installed paths:

```sh
HOUMAO_EXECUTION_INTEGRATION=1 \
HOUMAO_EXECUTION_ENTRYPOINT="$PWD/.pixi/envs/default/bin/houmao-mgr" \
HOUMAO_DSH_EXECUTABLE="$PWD/tmp/dsh/npm-runtime/node_modules/.bin/dsh" \
pixi run --as-is --offline python -m pytest tests/integration/execution/test_native_owner.py -q

HOUMAO_EXECUTION_INTEGRATION=1 \
HOUMAO_EXECUTION_ENTRYPOINT="$PWD/.pixi/envs/default/bin/houmao-mgr" \
HOUMAO_EXECUTION_CODEX_EXECUTABLE="$PWD/tmp/codex-floor/node_modules/@openai/codex-linux-arm64/vendor/aarch64-unknown-linux-musl/bin/codex" \
pixi run --as-is --offline python -m pytest tests/integration/execution/test_codex_owner.py -q
```

The executable paths above identify the local qualification installation, not packaged runtime dependencies. Ordinary test collection skips these opt-in tests when their explicit prerequisites are absent. Generated accounts, policies, keys, credential-bearing state, model requests, and tmux servers remain in fixture-owned scratch locations outside the checkout. Cleanup removes only recorded fixture resources.

## Evidence Key

Entries such as `A::function` identify the concrete test function in the linked file. Parameterized functions cover their declared variants. “Composed” means the requirement uses verified boundaries plus retained runtime behavior; it does not claim that every failure was injected into every native backend.

| Key | Test File |
| --- | --- |
| C | [Execution contracts and profile trust](../../../tests/unit/execution/test_contracts.py) |
| O | [Owner admission and environment](../../../tests/unit/execution/test_owner.py) |
| T | [Native transports and uncertainty](../../../tests/unit/execution/test_transports.py) |
| L | [Operator locator storage](../../../tests/unit/execution/test_locators.py) |
| A | [Owner application and operator router](../../../tests/unit/execution/test_application_router.py) |
| H | [CLI handoff](../../../tests/unit/execution/test_cli_handoff.py) |
| R | [Executor-managed target routing](../../../tests/unit/srv_ctrl/test_execution_routing.py) |
| K | [Runtime execution binding](../../../tests/unit/execution/test_runtime_context.py) |
| X | [Tmux scope contract](../../../tests/unit/execution/test_tmux.py) |
| S | [Runtime registry and lifecycle](../../../tests/unit/agents/realm_controller/test_runtime_registry.py) |
| M | [Retained manager behavior](../../../tests/unit/srv_ctrl/test_managed_agents.py) |
| F | [Communication-only imports](../../../tests/unit/srv_ctrl/commands/test_agents_external.py) |
| V | [Selected launch-source validation](../../../tests/unit/agents/test_native_launch_resolver.py) |
| PC | [Project launch behavior](../../../tests/unit/srv_ctrl/test_project_commands.py) |
| RF | [Native refresh command contract](../../../tests/unit/srv_ctrl/test_native_refresh_commands.py) |
| B | [Actual OS/SSH/tmux fixture boundaries](../../../tests/integration/execution/test_fixture_boundaries.py) |
| E | [Real product helper admission](../../../tests/integration/execution/test_owner_stdio.py) |
| N | [Actual DSH owner lifecycle](../../../tests/integration/execution/test_native_owner.py) |
| CX | [Actual Codex owner smoke](../../../tests/integration/execution/test_codex_owner.py) |

## Agent Execution Contexts

### Execution Profiles Select Existing Contexts Independently of Agent Backends

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Existing Linux account is selected without a password prompt | `B::test_restricted_operator_can_only_delegate_the_fixed_helper`; `E::test_real_owner_helper_admission_uses_actual_account_without_initializing`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner`; `CX::test_actual_codex_headless_owner_routing` | Real restricted sudo and native agents |
| Container and SSH profiles execute in their configured targets | `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner[tui-ssh]`; `T::test_native_argv_has_only_fixed_helper_and_transport_fields`; `C::test_transports_are_closed_and_independent_of_agent_backend` | Real SSH; Docker contract covered, live Docker deferred |
| Missing prerequisites do not trigger provisioning | `T::test_missing_helper_is_confirmed_pre_admission_failure`; `A::test_unconfigured_execution_target_cannot_spawn_transport`; `C::test_profile_loading_is_operator_scoped_and_non_mutating` | Component failure boundaries; product contains no account/container provisioning path |

### Only Trusted Configured Execution Routes Can Authorize Delegation

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Unconfigured target is rejected | `A::test_unconfigured_execution_target_cannot_spawn_transport`; `C::test_profile_loading_is_operator_scoped_and_non_mutating` | No transport spawn or state creation |
| Project content cannot supply a delegation command | `C::test_transports_are_closed_and_independent_of_agent_backend`; `C::test_invalid_or_credential_bearing_route_fields_are_rejected`; `O::test_operation_and_project_scope_are_checked_before_initialization`; `B::test_restricted_operator_can_only_delegate_the_fixed_helper` | Closed configuration, owner scope, and actual OS denial |
| Revoked delegation prevents later control | `R::test_failed_owner_control_never_replays_or_falls_back[rejected-False-transport_authorization_failed]`; `B::test_restricted_operator_can_only_delegate_the_fixed_helper`; `E::test_real_owner_helper_admission_uses_actual_account_without_initializing` | Composed transport-denial and no-fallback evidence; no claim of revoking every live native route |

### Launch Preparation and Environment Resolution Occur in the Owner Context

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Target-only paths are valid launch inputs | `H::test_launch_handoff_preserves_target_only_paths`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner`; `CX::test_actual_codex_headless_owner_routing` | No caller path validation; real owner-side project and file ownership |
| Caller and owner environments disagree | `O::test_dispatch_uses_target_environment_and_explicit_tmux_scope`; `O::test_scope_expansion_uses_observed_owner_home`; `T::test_transport_environment_excludes_operator_identity_and_delegation`; `B::test_owner_home_and_environment_do_not_use_operator_context` | Actual UID/HOME and component environment isolation |

### Execution Bindings Distinguish Identity, Ownership, and Controller Authority

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Binding records actual execution ownership | `O::test_context_initialization_records_actual_owner_and_stays_stable`; `C::test_binding_and_context_path_roundtrip_without_credentials`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner`; `CX::test_actual_codex_headless_owner_routing` | Actual owner/controller data and native manifest UID/GID |

### Existing Agents Remain Bound to Their Admitted Execution Context

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Profile edit cannot redirect a running agent | `T::test_changed_route_is_rejected_before_transport_spawn`; `C::test_fingerprint_pins_authority_but_allows_authentication_reference_rotation`; `O::test_changed_saved_context_is_rejected_without_rewriting_it`; `K::test_local_controller_refuses_replaced_context_without_repair`; `E::test_real_owner_helper_admission_uses_actual_account_without_initializing` | Saved-route, target-context, and actual helper drift rejection |
| Relaunch preserves execution ownership | `S::test_start_resume_send_prompt_and_stop_refresh_registry`; `R::test_stop_and_relaunch_return_owner_qualified_cleanup_authority`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Fresh runtime generation with preserved binding; real owner lifecycle |

### Agent Instances Under One Account Retain Independent Credential Bindings

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Two agents share an owner and use different private keys | `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Both native routes launch two same-owner/profile agents; distinct projected Ed25519 digests survive refresh/stop/relaunch and sibling generation stays unchanged |

### Operator Delegation Credentials Are Excluded From Agent Execution

| Scenario | Evidence | Scope |
| --- | --- | --- |
| SSH transport authentication is not an agent credential | `T::test_native_argv_has_only_fixed_helper_and_transport_fields`; `T::test_transport_environment_excludes_operator_identity_and_delegation`; `O::test_dispatch_uses_target_environment_and_explicit_tmux_scope`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner[tui-ssh]` | No SSH-agent forwarding; separate transport key and explicitly selected native credential files |

### Bounded Operations Use Owner-Side Runtime Authority

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Controls use the owner even when the caller has a matching session name | `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner`; `R::test_exact_executor_target_resolves_before_local_control`; `B::test_tmux_servers_with_identical_session_names_remain_distinct` | Native controls preserve the operator namesake and owner sibling; component active/stopped routing |
| Generation changes before a mutation is admitted | `A::test_owner_control_checks_exact_authority_before_reconstruction`; `A::test_owner_control_rechecks_authority_after_resolution`; `R::test_failed_owner_control_never_replays_or_falls_back[rejected-False-generation_conflict]` | Pre/post reconstruction identity, binding, and generation fencing |
| Interactive attach is unsupported by a bounded transport | `R::test_unsupported_finite_operation_has_no_local_controller_fallback` | Explicit unsupported outcome before local control |

### Owner-Side Tmux Operations Use an Explicit Server Binding

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Inherited operator tmux variables do not redirect delegation | `X::test_scoped_commands_clear_inherited_tmux_without_mutating_parent`; `X::test_libtmux_receives_explicit_socket`; `K::test_concurrent_controllers_restore_their_own_owner_and_socket`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Both command/libtmux paths and real private owner sockets |
| Stop preserves sibling agent and user sessions | `B::test_tmux_servers_with_identical_session_names_remain_distinct`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Actual selected-session teardown preserves sibling and operator sessions |

### Inspection and Home Refresh Preserve Execution Context and Existing Semantics

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Remote home inspection returns a qualified path without local mutation | `R::test_home_and_refresh_are_owner_qualified_without_local_materialization`; `S::test_start_resume_send_prompt_and_stop_refresh_registry`; `A::test_reconstruction_is_read_only_and_explicit_operation_retains_its_scope`; `E::test_real_owner_helper_admission_uses_actual_account_without_initializing`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner[tui-ssh]` | Qualified owner path, unchanged reconstruction file snapshot, no missing-context repair, and real SSH home query |
| Refresh runs under the owner without restarting | `R::test_home_and_refresh_are_owner_qualified_without_local_materialization`; `RF::test_detached_local_reads_and_automatic_refresh_never_mutate`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Real native refresh preserves generation and both selected keys; retained no-restart contract |

### Transport Failure Preserves Uncertainty Without Replaying Mutations

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Relaunch response is lost after admission | `T::test_timeout_does_not_resubmit_mutation`; `T::test_failed_result_retains_uncertainty_without_secret_diagnostics`; `O::test_stdio_is_framed_and_admitted_failure_is_indeterminate`; `R::test_failed_owner_control_never_replays_or_falls_back[indeterminate-None-transport_timeout]` | Actual helper-pipe timeout and admitted-failure injection; no claim that every native backend lost a relaunch response |

### Execution Transports Do Not Broaden Communication-Only or Public HTTP Authority

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Communication-only import remains unable to relaunch | `F::test_external_target_rejects_local_lifecycle_operations`; `F::test_external_cleanup_selector_is_rejected_before_local_scan`; `F::test_external_resolution_preserves_local_lifecycle_precedence` | Retained lifecycle rejection and separate import collection |
| Public listener cannot request a user switch | `A::test_public_http_launch_contract_cannot_supply_execution_authority` | Maintained HTTP launch DTO rejects executor/controller fields; execution handoff remains private CLI/stdin plumbing |

## Owner Registry and Operator Locators

### Owner Lifecycle Records Preserve Execution Bindings

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Stopped agent retains execution ownership | `S::test_start_resume_send_prompt_and_stop_refresh_registry`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Persisted stop/relaunch authority and actual native stopped revival |
| Relaunch updates presence without changing owner | `S::test_start_resume_send_prompt_and_stop_refresh_registry`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | New live generation, same binding and logical ID |

### Operator Execution Locators Remain Separate From Runtime Presence and Communication Imports

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Delegated launch publishes a routing locator after owner admission | `L::test_publish_load_and_list_do_not_open_foreign_paths`; `A::test_failed_operator_publication_reports_admitted_identity_without_second_birth`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Strict separate locator collection and actual post-birth controls |
| Foreign path and loopback endpoint are not local authority | `L::test_publish_load_and_list_do_not_open_foreign_paths`; `R::test_owner_gateway_loopback_endpoint_is_context_qualified`; `R::test_equivalent_owner_record_deduplicates_without_local_manifest_open` | No foreign path open or caller-loopback substitution |
| Conflicting bindings cannot replace an existing logical identity | `L::test_same_id_different_binding_cannot_replace_known_owner`; `L::test_local_identity_conflict_is_checked_before_locator_publication`; `L::test_later_local_publication_cannot_shadow_existing_executor_owner` | Both publication orders share the per-ID ownership lock |

### Local Registry Cleanup Cannot Infer Foreign Liveness or Remove Owner State

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Local tmux absence preserves execution locator | `L::test_publish_load_and_list_do_not_open_foreign_paths`; `R::test_lifecycle_inclusive_listing_retains_unavailable_owner_as_unknown`; retained local cleanup scans only `live_agents/` | Composed separate-collection and no-false-liveness evidence |
| Locator removal leaves owner runtime intact | `L::test_forget_removes_only_lexical_locator_and_preserves_other_collections`; `L::test_forget_symlinked_entry_preserves_external_target`; `L::test_symlinked_collection_is_never_followed` | Lexical operator mutation only; no owner transport invocation |

### Failed Operator Publication Preserves an Admitted Owner Launch

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Operator cannot publish after owner launch | `A::test_failed_operator_publication_reports_admitted_identity_without_second_birth`; `L::test_atomic_replace_failure_leaves_no_orphan_temporary_file` | Injected operator write failure, admitted identity preserved, no second birth |
| Explicit reconciliation repairs only the routing locator | `A::test_reconciliation_publishes_only_existing_owner_locator`; `L::test_same_id_different_binding_cannot_replace_known_owner`; `H::test_admin_executor_commands_are_available` | One describe plus an atomic operator publication; no launch operation |

## Project Launch

### Project Launch Supports Explicit Execution-Profile Selection

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Launch profile and execution profile select different concerns | `H::test_launch_handoff_preserves_target_only_paths`; `A::test_owner_launch_reuses_shared_service_and_output_collector`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Explicit executor before target project-source resolution |
| Omitted executor preserves current-account birth | `PC::test_project_agents_launch_uses_profile_defaults_and_overrides`; `S::test_start_resume_send_prompt_and_stop_refresh_registry`; `K::test_controller_refuses_wrong_actual_os_owner` | Composed retained CLI behavior and newly persisted actual local owner |

### Delegated Launch Validates Target Inputs Before Preparing Runtime State

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Remote-only project and workdir pass owner-side validation | `H::test_launch_handoff_preserves_target_only_paths`; `A::test_owner_launch_reuses_shared_service_and_output_collector`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Caller denied project access; actual owner birth succeeds |
| Invalid selected target source has no caller-local fallback | `V::test_resolve_native_launch_target_fails_for_selected_invalid_system_skill`; `A::test_owner_launch_reuses_shared_service_and_output_collector`; `R::test_failed_owner_control_never_replays_or_falls_back` | Composed selected-source validation, shared target-side service, and no-fallback contract |
| Unrelated invalid target profile does not block launch | `V::test_resolve_native_launch_target_ignores_unselected_invalid_preset_for_explicit_path`; `A::test_owner_launch_reuses_shared_service_and_output_collector` | Retained selected-source-scoped validation through the shared owner launch boundary |

## Manager Discovery and Lifecycle

### Agent Post-Launch Commands Use Registry-First Discovery

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Post-launch command discovers active agent via shared registry | `M::test_resolve_managed_agent_target_prefers_shared_registry_for_local_records`; `R::test_exact_executor_target_resolves_before_local_control` | Local and delegated managed tiers precede pair fallback |
| Live command rejects stopped registry target | `M::test_resolve_managed_agent_target_rejects_stopped_local_record`; `A::test_owner_control_checks_exact_authority_before_reconstruction` | Retained owner lifecycle gate and exact authority validation |
| Post-launch command falls back to port when no registry record exists | `M::test_resolve_managed_agent_target_falls_back_to_server_when_registry_misses`; `R::test_explicit_port_skips_execution_locator_lookup` | Fallback exists only without a selected execution locator |
| Local tmux-backed agent is controlled directly without a server | `M::test_resolve_managed_agent_target_prefers_shared_registry_for_local_records`; `S::test_start_resume_send_prompt_and_stop_refresh_registry`; `CX::test_actual_codex_headless_owner_routing` | Retained controller path and actual serverless owner workflow |
| Unreachable executor does not fall through to a local namesake | `R::test_failed_owner_control_never_replays_or_falls_back`; `R::test_exact_executor_target_resolves_before_local_control` | Explicit route failure without local reconstruction or default pair access |

### Registry-Backed Discovery Includes External Communication-Only Records

| Scenario | Evidence | Scope |
| --- | --- | --- |
| External record resolves after local lifecycle lookup | `F::test_external_target_routes_state_prompt_gateway_and_mail_to_remote_pair`; `F::test_external_resolution_preserves_local_lifecycle_precedence` | Existing communication-only route retained |
| Local lifecycle record takes precedence over external alias | `F::test_external_resolution_preserves_local_lifecycle_precedence` | Existing managed-tier precedence retained |
| Explicit port bypass remains unchanged | `F::test_external_resolution_does_not_intercept_explicit_port`; `R::test_explicit_port_skips_execution_locator_lookup` | Local, execution, and import lookup bypassed |

### Executor-Aware Selectors Preserve Identity Across Execution Contexts

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Same friendly name under different users requires disambiguation | `L::test_exact_id_never_chooses_a_friendly_name_or_tmux_alias`; `R::test_friendly_name_conflict_is_reported_before_owner_control` | ID/context candidates surfaced before dispatch |
| Identical tmux names do not identify an executor | `L::test_exact_id_never_chooses_a_friendly_name_or_tmux_alias`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Session-name aliases stay local; actual namesakes remain untouched |

### Executor-Managed Lifecycle Commands Use Owner Authority for Active and Stopped Agents

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Delegated stopped agent is relaunched through its owner | `R::test_exact_executor_target_resolves_before_local_control`; `R::test_stop_and_relaunch_return_owner_qualified_cleanup_authority`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | No caller manifest scan; actual stopped native revival |
| Stop returns owner-qualified cleanup information | `R::test_stop_and_relaunch_return_owner_qualified_cleanup_authority`; `N::test_native_dsh_launch_control_refresh_and_relaunch_keep_owner` | Context-qualified manifest/session root, durable locator retained |

### Execution-Locator Listing Distinguishes Observed Lifecycle From Unverified State

| Scenario | Evidence | Scope |
| --- | --- | --- |
| Active delegated agent appears without a local session | `R::test_verified_executor_appears_in_active_listing_without_local_presence` | Verified owner state is sufficient for active listing |
| Unavailable owner remains a known unverified target | `R::test_lifecycle_inclusive_listing_retains_unavailable_owner_as_unknown`; `R::test_unknown_transport_cannot_claim_a_live_or_local_agent` | Unknown transport/lifecycle remains explicit, without false stopped state |

## Remaining Qualification Boundary

The deferred item is real Docker execution against a deliberately prepared existing container. Native argv and immutable-ID validation do not establish container launch/control qualification. The host qualification above covers restricted sudo, SSH, DSH ACP/Web, and a focused Codex headless smoke. Strong isolation between agents sharing a UID, public network authentication, asset deployment, interactive forwarding, and cross-context migration remain outside this change.
