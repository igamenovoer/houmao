## 1. Demo Engine Control Input

- [x] 1.1 Extend `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` with backward-compatible control-input state and artifact support, including a dedicated `controls/` workspace directory, a structured control record model, and reset/load helpers that keep prompt turns separate.
- [x] 1.2 Add a `send-keys` demo subcommand with one required positional key-stream argument plus `--as-raw-string`, and delegate it to `brain_launch_runtime send-keys` using the persisted active `agent_identity`.
- [x] 1.3 Persist one control-input record plus captured stdout/stderr logs for each `send-keys` invocation, and keep `verify` plus prompt-turn accounting unchanged so control input is never counted as a turn.

## 2. Demo Pack Workflow

- [x] 2.1 Extend `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh` so the advanced shell interface exposes `send-keys` with a required positional key stream, documents that usage, and forwards the new arguments through the existing workspace/default resolution flow.
- [x] 2.2 Add a `scripts/demo/cao-interactive-full-pipeline-demo/send_keys.sh` wrapper that reuses `run_demo.sh`, requires one positional key stream, and works from arbitrary working directories.
- [x] 2.3 Update `scripts/demo/cao-interactive-full-pipeline-demo/README.md` so the main walkthrough and appendix document when to use prompt turns versus control input, include concrete `send-keys` examples, and list the generated `controls/` artifacts.

## 3. Coverage And Validation

- [x] 3.1 Extend `tests/integration/demo/test_cao_interactive_full_pipeline_demo_cli.py` fake tool harnesses so they emulate runtime `send-keys` behavior and record the forwarded control-input arguments.
- [x] 3.2 Add integration coverage for the new control-input wrapper and CLI flow, including the required positional key stream, `--as-raw-string` pass-through, and the invariant that `verify` still reports prompt turns only.
- [x] 3.3 Run the targeted demo integration test suite plus any relevant lint/type checks touched by the change and capture the results in the implementation notes or commit context.
