## Why

The interactive CAO demo now has the right runtime behavior, but it still reads like a maintainer-oriented lifecycle utility instead of a tutorial a human can follow step by step. We need to reshape the pack around an operator workflow that launches a named agent (`alice`), lets the user drive prompts manually, and makes the critical commands obvious from the README.

## What Changes

- Rewrite the interactive demo README into a tutorial-style document following the repository's API usage tutorial guidance, with explanatory text and inline code blocks for each critical step.
- Add simple shell entrypoints for the main manual workflow: launch the agent as `alice`, send one inline prompt with `--prompt`, and stop the active session, while reusing `run_demo.sh` as the shared shell backend so the tutorial and advanced commands operate on one consistent workspace and environment.
- Keep the existing lower-level lifecycle CLI available, but reposition it as the underlying engine and advanced interface rather than the primary tutorial surface.
- Shift report verification and snapshot behavior out of the main happy path so the tutorial is intentionally open-ended instead of automatically running to completion, while preserving `verify` as optional maintainer tooling for the existing minimum two-turn regression contract.

## Capabilities

### New Capabilities
- `cao-interactive-demo-operator-workflow`: Operator-facing tutorial and wrapper-script workflow for launching, chatting with, inspecting, and stopping the interactive CAO Claude demo.

### Modified Capabilities
- None.

## Impact

- Affected code: `scripts/demo/cao-interactive-full-pipeline-demo/` documentation and shell entrypoints, plus any supporting Python CLI defaults or output needed by the new tutorial.
- Affected validation: manual developer review of the wrapper-script flow and README-driven command surfaces, with any shell syntax checks treated as lightweight author aids rather than new Pixi tasks or release-gating automation.
- Dependencies/systems: local `pixi`, local `tmux`, fixed CAO loopback access at `http://127.0.0.1:9889`, and Claude credential/profile inputs already used by the existing demo.
