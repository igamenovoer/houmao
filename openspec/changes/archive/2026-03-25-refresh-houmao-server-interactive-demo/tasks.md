## 1. Align the demo pack with the shared fixture source

- [x] 1.1 Replace `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents` with the tracked relative symlink to `tests/fixtures/agents/`.
- [x] 1.2 Update any repo-owned demo layout checks or verification helpers so they assert that the shipped `agents` entry resolves to the fixture tree.

## 2. Refresh operator-facing startup documentation

- [x] 2.1 Update `scripts/demo/houmao-server-interactive-full-pipeline-demo/README.md` to describe the current demo-owned `houmao-server` native headless launch flow and the shared fixture-backed `agents` source.
- [x] 2.2 Update `scripts/demo/houmao-server-interactive-full-pipeline-demo/run_demo.sh` and `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/cli.py` help text to remove retired `houmao-mgr cao launch` wording and describe the native launch budget accurately.

## 3. Restore the documented startup budget behavior

- [x] 3.1 Update `start_demo()` so the native launch client uses `env.compat_create_timeout_seconds` when calling the server-backed headless launch flow.
- [x] 3.2 Keep the existing persisted server-backed state contract (`api_base_url`, `session_name`, `terminal_id`, `agent_ref`, `houmao_server`) unchanged while applying the timeout fix.

## 4. Validate the refreshed demo contract

- [x] 4.1 Update or add targeted coverage for the symlinked demo layout, refreshed startup wording, and the create-timeout wiring.
- [x] 4.2 Run the relevant lint/tests or demo verification commands needed to confirm the refreshed demo remains implementation-ready.
