## 1. Demo Startup Budget Plumbing

- [x] 1.1 Add demo-owned compatibility startup timeout fields and defaults to the interactive demo models and CLI argument resolution.
- [x] 1.2 Update the demo startup server command to pass the configured compatibility shell-ready, provider-ready, and Codex warmup overrides into `houmao-server serve`.
- [x] 1.3 Update the detached compatibility launch command to pass the configured create-timeout override into `houmao-mgr cao launch --headless`.
- [x] 1.4 Forward matching environment-based overrides through `scripts/demo/houmao-server-interactive-full-pipeline-demo/run_demo.sh`.

## 2. Docs And Regression Coverage

- [x] 2.1 Update the interactive demo README and shell-wrapper help text to describe the demo-owned generous startup budgets and override surface.
- [x] 2.2 Update `tests/unit/demo/test_houmao_server_interactive_full_pipeline_demo.py` to assert the demo passes the expected compatibility timeout overrides into both server startup and detached launch commands.

## 3. Validation

- [x] 3.1 Run the focused interactive demo unit tests covering startup command construction and timeout override forwarding.
