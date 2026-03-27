## ADDED Requirements

### Requirement: Demo pack exercises TUI join lifecycle end-to-end

The repository SHALL provide a demo pack at `scripts/demo/agents-join-demo-pack/` that exercises the `houmao-mgr agents join` TUI adoption lifecycle through these stages: start a supported provider TUI in a tmux session, join the session into Houmao control, inspect the joined agent state, submit a prompt through the managed-agent path, and stop the joined agent.

The demo pack SHALL default to `claude_code` as the provider and SHALL accept an optional `--provider` argument to select `codex` or `gemini_cli` instead.

#### Scenario: Operator runs the TUI join demo end-to-end with default provider

- **WHEN** an operator runs the demo pack's orchestrator script without specifying a provider
- **THEN** the demo starts a Claude Code TUI in a new tmux session
- **AND THEN** it joins the session with `houmao-mgr agents join --agent-name <demo-name>`
- **AND THEN** it inspects the joined agent with `houmao-mgr agents state --agent-name <demo-name>`
- **AND THEN** the joined agent is visible in the shared registry
- **AND THEN** it stops the joined agent with `houmao-mgr agents stop --agent-name <demo-name>`

#### Scenario: Operator runs the TUI join demo with an alternate provider

- **WHEN** an operator runs the demo pack's orchestrator script with `--provider codex`
- **THEN** the demo starts a Codex TUI in a new tmux session instead of Claude Code
- **AND THEN** it completes the same join → inspect → stop lifecycle using the Codex provider

### Requirement: Demo pack includes a README documenting prerequisites, quick start, and expected outputs

The demo pack directory SHALL contain a `README.md` that documents: prerequisites (tmux, pixi, a working provider CLI), quick start commands, step-by-step walkthrough of what each script does, and expected terminal output at each stage.

The README SHALL include a Mermaid sequence diagram illustrating the join lifecycle stages exercised by the demo.

#### Scenario: Reader can follow the demo README to completion

- **WHEN** a reader follows the demo pack README from prerequisites through quick start
- **THEN** they can execute the demo and observe the expected outputs at each stage
- **AND THEN** the Mermaid diagram in the README matches the actual script execution flow

### Requirement: Demo pack scripts follow established conventions

The demo pack SHALL follow the shell script conventions used by existing demo packs in `scripts/demo/`: individual scripts per lifecycle step, a `run_demo.sh` orchestrator, and explicit error handling with non-zero exit on failure.

The demo pack SHALL NOT require an agent definition directory, brain recipes, config profiles, or credential profiles — the join workflow does not need them.

#### Scenario: Demo pack structure matches existing demo pack conventions

- **WHEN** a developer inspects `scripts/demo/agents-join-demo-pack/`
- **THEN** they find a `README.md`, a `run_demo.sh` orchestrator, and individual step scripts
- **AND THEN** the pack does not contain an `agents/` directory or brain recipe files
