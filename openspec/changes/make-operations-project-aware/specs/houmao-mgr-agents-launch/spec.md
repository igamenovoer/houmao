## MODIFIED Requirements

### Requirement: `houmao-mgr agents launch` performs local brain building and agent launch
`houmao-mgr agents launch` SHALL perform the full agent launch pipeline locally without requiring a running `houmao-server`.

The pipeline SHALL follow this sequence:
1. Resolve the active project-aware local roots when the command is operating in project context.
2. Parse the effective `agents/` source tree into the canonical parsed catalog.
3. Resolve the native launch target from the `--agents` selector and `--provider` against that parsed catalog.
4. Resolve the selected preset to its effective tool, role, setup, skills, launch settings, and effective auth as one resolved launch/build specification.
5. Build the brain home using the effective runtime root.
6. Start the runtime session using the effective runtime root and jobs root.
7. Publish a `LiveAgentRegistryRecordV2` to the shared registry.

When no active project overlay exists for the caller and no stronger overlay selection override is supplied, maintained local `agents launch` SHALL ensure `<cwd>/.houmao` exists before continuing.

When the command is operating in project context and no stronger runtime-root or jobs-root override exists, it SHALL use:

- runtime root: `<active-overlay>/runtime`
- jobs root: `<active-overlay>/jobs`

#### Scenario: Project-context agents launch uses overlay-local runtime and jobs roots
- **WHEN** an active project overlay resolves as `/repo/.houmao`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** no stronger runtime-root or jobs-root override is supplied
- **THEN** the command builds brain state under `/repo/.houmao/runtime`
- **AND THEN** it starts the session with a job dir derived under `/repo/.houmao/jobs/<session-id>/`
- **AND THEN** it still publishes the launched agent to the shared registry

#### Scenario: Missing overlay is bootstrapped before maintained local launch
- **WHEN** no active project overlay exists
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **THEN** the command ensures `<cwd>/.houmao` exists before parsing presets and building brain state
- **AND THEN** the resulting overlay becomes the default local root family for that launch
