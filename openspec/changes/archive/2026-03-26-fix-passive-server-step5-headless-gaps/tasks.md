## 1. Launch Publication and Validation

- [x] 1.1 Add explicit shared-registry publication to `HeadlessAgentService.launch()` after `start_runtime_session()` succeeds and before the launch response is returned
- [x] 1.2 Add launch rollback/cleanup behavior when shared-registry publication fails after runtime startup
- [x] 1.3 Validate `brain_manifest_path` contents in `HeadlessAgentService.launch()` and reject requests whose `tool` does not match the manifest `inputs.tool`
- [x] 1.4 Validate optional `role_name` before launch and return contract-matching client errors for invalid roles
- [x] 1.5 Forward the full mailbox option set, including Stalwart-specific fields, into `start_runtime_session()`
- [x] 1.6 Normalize launch-time validation failures to the intended 422-style client error path

## 2. Managed Identity Resolution

- [x] 2.1 Introduce a managed-headless resolution helper that translates discovered/shared-registry agent references into the authoritative managed `tracked_agent_id`
- [x] 2.2 Update `submit_turn()` in `PassiveServerService` to use the managed resolution helper instead of raw registry `agent_id`
- [x] 2.3 Update `interrupt_agent()` in `PassiveServerService` to prefer the authoritative managed-headless path for server-launched agents
- [x] 2.4 Update `stop_agent()` in `PassiveServerService` to route server-launched agents through managed cleanup even when callers use the published shared-registry `agent_id`

## 3. Restart Resume

- [x] 3.1 Update `HeadlessAgentService._rebuild_handles()` to resume live authorities with `resume_runtime_session()` instead of rebuilding `controller=None` placeholders
- [x] 3.2 Handle resume failures by logging the broken authority and cleaning up stale persisted state when the session is not recoverable
- [x] 3.3 Ensure rebuilt handles preserve the identity information needed by managed route resolution after restart

## 4. Turn Finalization and Artifact Persistence

- [x] 4.1 Replace the simplified turn-worker completion update with a durable turn-record refresh step that captures artifact paths and completion metadata
- [x] 4.2 Persist `stdout_path`, `stderr_path`, `status_path`, `completion_source`, and final status/return code in `ManagedHeadlessTurnRecord` when artifacts exist
- [x] 4.3 Update turn events loading to consume the finalized turn record and durable artifacts instead of an incompletely populated record
- [x] 4.4 Update turn artifact retrieval to succeed for completed turns whose stdout/stderr files were written by the headless runtime

## 5. Tests and Verification

- [x] 5.1 Add unit tests covering explicit shared-registry publication on launch and rollback when publication fails
- [x] 5.2 Add tests covering managed follow-up route resolution for both `tracked_agent_id` and a custom published `agent_id`
- [x] 5.3 Add restart tests showing a live persisted authority resumes to an operable controller and a stale authority is cleaned up
- [x] 5.4 Add turn-finalization tests covering persisted artifact paths, events loading, and artifact endpoint success after completion
- [x] 5.5 Add launch validation tests for manifest tool mismatch, invalid role, 422 responses, and Stalwart mailbox passthrough
- [x] 5.6 Run the passive-server unit suite plus targeted lint/typecheck validation for the corrected implementation
