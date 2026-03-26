## 1. Refactor startup and persisted state

- [x] 1.1 Replace the demo-owned `houmao-server` startup path in `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/` with local brain build plus detached local interactive runtime launch.
- [x] 1.2 Revise the demo path/layout helpers so run roots keep local runtime, registry, jobs, and worktree ownership but no longer depend on demo-owned server directories or server logs.
- [x] 1.3 Update the persisted demo state models to store `agent_name`, `agent_id`, `tmux_session_name`, `session_manifest_path`, and related local-runtime fields instead of `api_base_url`, `agent_ref = session_name`, and `houmao_server` bridge metadata.
- [x] 1.4 Update startup option handling and wrapper inputs so provider selection, session-name requests, and the stable `launch_alice.sh` path map to the revised local identity model.

## 2. Refactor local control, inspect, and verification flows

- [x] 2.1 Rework inspect to resolve the launched local managed agent through shared-registry/controller surfaces and collect live managed-agent state, detail, history, and optional dialog-tail evidence from local TUI tracking.
- [x] 2.2 Rework prompt and interrupt flows to use the local managed-agent control path instead of direct `houmao-server` HTTP requests.
- [x] 2.3 Rework stop and partial-start cleanup to use the local runtime controller and best-effort local tmux/runtime cleanup rather than server-backed stop/delete operations.
- [x] 2.4 Rework verification and generated report payloads so they validate the run through local prompt acceptance plus local tracked state/history evidence and record the revised identity fields.

## 3. Update operator-facing demo contract

- [x] 3.1 Rewrite `scripts/demo/houmao-server-interactive-full-pipeline-demo/README.md` to describe the serverless/local workflow, revised identity model, and updated run-root artifacts.
- [x] 3.2 Update the shell wrappers and any emitted help text so they no longer mention demo-owned `houmao-server` startup, server route semantics, or server-specific timeout overrides.
- [x] 3.3 Ensure the demo's machine-readable startup, inspect, interrupt, prompt, verify, and stop artifacts remain coherent under the revised local contract.

## 4. Test and validate the revised demo

- [x] 4.1 Update unit tests for the demo state model, startup flow, and local control helpers to assert the revised serverless contract.
- [x] 4.2 Update integration tests for the demo CLI workflow to assert local launch, local inspect/control behavior, and the revised identity/state artifacts.
- [x] 4.3 Run the relevant demo-focused test commands and any required spec validation so the revised change is ready for implementation handoff.
