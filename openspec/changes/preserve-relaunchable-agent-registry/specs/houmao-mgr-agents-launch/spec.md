## MODIFIED Requirements

### Requirement: `houmao-mgr agents launch` performs local brain building and agent launch
`houmao-mgr agents launch` SHALL perform the full agent launch pipeline locally without requiring a running `houmao-server`.

The pipeline SHALL follow this sequence:
1. Resolve the launch source context from the invocation project-aware context or from the resolved explicit preset source.
2. Resolve the runtime workdir from `--workdir` when supplied, otherwise from the invocation cwd.
3. Parse the effective `agents/` source tree from the launch source context into the canonical parsed catalog.
4. Resolve the native launch target from the `--agents` selector and `--provider` against that parsed catalog.
5. Resolve the selected preset to its effective tool, role, setup, skills, launch settings, and effective auth as one resolved launch/build specification.
6. Build the brain home using the effective runtime root selected from the launch source context.
7. Start the runtime session using the effective runtime root and jobs root from the launch source context together with the runtime workdir from step 2.
8. Publish an active lifecycle-aware managed-agent registry record to the shared registry.

The published record SHALL include durable managed-agent identity and runtime locator metadata sufficient for later lifecycle commands, including stop, relaunch, and cleanup.

When the launch source belongs to a Houmao project and no stronger runtime-root or jobs-root override is supplied, maintained local `agents launch` SHALL use that source project's overlay-local defaults rather than deriving project roots from `--workdir`.

When no active project overlay exists for the selected launch source and no stronger overlay selection override is supplied, maintained local `agents launch` SHALL ensure the selected source overlay candidate exists before continuing.

When the command is operating in project context and no stronger runtime-root or jobs-root override exists, it SHALL use:

- runtime root: `<active-overlay>/runtime`
- jobs root: `<active-overlay>/jobs`

#### Scenario: Project-context agents launch keeps overlay-local runtime and jobs roots when `--workdir` points elsewhere
- **WHEN** an active project overlay resolves as `/repo-a/.houmao`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --workdir /repo-b`
- **AND WHEN** no stronger runtime-root or jobs-root override is supplied
- **THEN** the command builds brain state under `/repo-a/.houmao/runtime`
- **AND THEN** it starts the session with a job dir derived under `/repo-a/.houmao/jobs/<session-id>/`
- **AND THEN** it records `/repo-b` as the runtime workdir for the launched session
- **AND THEN** it publishes the launched agent as an active lifecycle-aware managed-agent registry record

#### Scenario: Explicit preset path launch uses the preset source project rather than `--workdir`
- **WHEN** an explicit preset path resolves under source project `/source-repo/.houmao/agents/presets/`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents /source-repo/.houmao/agents/presets/reviewer-codex-default.yaml --provider codex --workdir /target-repo`
- **THEN** the command resolves the launch source context from `/source-repo`
- **AND THEN** it uses `/source-repo/.houmao/runtime` and `/source-repo/.houmao/jobs` as the project-aware defaults
- **AND THEN** it records `/target-repo` as the runtime workdir for the launched session

#### Scenario: Missing overlay is bootstrapped from the launch source rather than the runtime workdir
- **WHEN** no active project overlay exists for the selected launch source
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --workdir /repo-b`
- **THEN** the command ensures the selected source overlay candidate exists before parsing presets and building brain state
- **AND THEN** it does not bootstrap `/repo-b/.houmao` only because `/repo-b` was selected as the runtime workdir

#### Scenario: Launch publishes active lifecycle registry metadata
- **WHEN** `houmao-mgr agents launch` successfully starts a local tmux-backed managed agent
- **THEN** the shared registry record has lifecycle state `active`
- **AND THEN** the record includes active liveness metadata for live command routing
- **AND THEN** the record includes durable manifest, session-root, and agent-definition locators for later stop, relaunch, and cleanup
