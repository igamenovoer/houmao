## ADDED Requirements

### Requirement: `houmao-srv-ctrl launch --headless` targets `houmao-server` native headless launch
When an operator invokes `houmao-srv-ctrl launch` with the additive `--headless` flag against a supported Houmao pair, `houmao-srv-ctrl` SHALL treat that invocation as a Houmao-owned native headless launch path rather than delegating that headless case to `cao launch`.

That native headless launch path SHALL target a Houmao-owned `houmao-server` endpoint for headless launch and SHALL use the server-returned managed-agent identity and runtime pointers for any follow-up reporting or artifact materialization required by the pair.

For the headless case, `houmao-srv-ctrl` SHALL translate pair convenience inputs such as `--agents`, `--provider`, and the current working directory into the resolved native launch request expected by `houmao-server`.

That translation SHALL produce the resolved runtime launch inputs required by the raw server contract, such as `tool`, `working_directory`, `agent_def_dir`, `brain_manifest_path`, and `role_name`, or SHALL fail explicitly before launch if it cannot resolve them.

The non-headless `launch` path MAY remain delegated to `cao` for CAO-compatible TUI behavior in the shallow cut.

#### Scenario: Headless launch does not delegate to `cao`
- **WHEN** an operator runs `houmao-srv-ctrl launch --headless --agents gpu-kernel-coder --provider claude_code`
- **THEN** `houmao-srv-ctrl` routes that request to `houmao-server` native headless launch
- **AND THEN** it does not require `cao launch` to create a CAO session or terminal for that headless agent

#### Scenario: Headless convenience inputs are translated into the native request model
- **WHEN** an operator runs `houmao-srv-ctrl launch --headless --agents gpu-kernel-coder --provider claude_code`
- **THEN** `houmao-srv-ctrl` resolves those convenience inputs into the native headless launch request expected by `houmao-server`
- **AND THEN** the raw server contract does not need to accept `--agents` or `--provider` as its normative launch fields

#### Scenario: Non-headless launch keeps delegated CAO behavior
- **WHEN** an operator runs `houmao-srv-ctrl launch --agents gpu-kernel-coder --provider codex` without `--headless`
- **THEN** `houmao-srv-ctrl` may continue delegating that launch to `cao`
- **AND THEN** the CAO-compatible TUI launch path remains available alongside the Houmao-native headless extension
