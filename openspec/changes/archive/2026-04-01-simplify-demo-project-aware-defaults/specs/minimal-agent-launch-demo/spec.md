## MODIFIED Requirements

### Requirement: The demo remains tutorial-shaped and records reproducible outputs

The supported demo SHALL include:
- one tutorial markdown document,
- one tracked prompt input,
- one runnable script,
- one generated outputs area for the produced working tree and command artifacts.

The tutorial SHALL explain prerequisites, the provider selection input, the generated outputs, verification steps, and common failure modes.

The maintained runner and tutorial SHALL describe one generated project-aware overlay root for each run as the local Houmao-owned state anchor. The maintained demo SHALL NOT require separate root env overrides for agent-definition and runtime placement merely to keep the run self-contained.

Important generated outputs for every lane SHALL include:
- `workdir/.houmao/agents/`: generated launch tree with the demo-local auth alias
- `workdir/.houmao/runtime/`: built homes, manifests, and session artifacts
- `workdir/.houmao/jobs/`: overlay-local per-session job directories when the run materializes them
- `logs/preflight-stop.log`: best-effort cleanup of a stale agent with the same demo name
- `logs/launch.log`
- `logs/state.log`
- `summary.json`

Headless-only generated outputs SHALL include:
- `logs/prompt.log`
- `logs/stop.log`

#### Scenario: Reader follows the tutorial document
- **WHEN** a reader opens the minimal demo tutorial
- **THEN** they find an explicit question, prerequisites, implementation idea, run command, representative outputs, verification guidance, and troubleshooting notes
- **AND THEN** the full runnable flow points to the tracked script rather than embedding the entire implementation inline

## ADDED Requirements

### Requirement: The minimal demo uses one generated overlay root for local Houmao-owned state

The maintained `scripts/demo/minimal-agent-launch/` runner SHALL select one generated overlay root for each run and rely on that overlay-local default contract for agent definitions, runtime state, and jobs placement.

The maintained runner MAY continue to use one explicit `HOUMAO_PROJECT_OVERLAY_DIR` override to point the CLI at that generated overlay when the selected output root is outside the repository tree, but it SHALL NOT require separate agent-definition or runtime-root env overrides only to keep the demo self-contained.

#### Scenario: One overlay selector anchors the generated run tree
- **WHEN** an operator runs the maintained minimal demo for any supported lane
- **THEN** the generated run tree selects one project-aware overlay root under that lane's output root
- **AND THEN** the launch resolves agent definitions, runtime state, and jobs state from that one selected overlay rather than from separate root env overrides
