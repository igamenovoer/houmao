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
8. Publish a `LiveAgentRegistryRecordV2` to the shared registry.

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
- **AND THEN** it still publishes the launched agent to the shared registry

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

### Requirement: `houmao-mgr agents launch` accepts the established launch options

`houmao-mgr agents launch` SHALL accept at minimum:

- `--agents` (required): Native launch selector to resolve the preset
- `--provider` (required or defaulted): Provider identifier (`claude_code`, `codex`, `gemini_cli`, etc.)
- `--agent-name`: Optional logical managed-agent name
- `--agent-id`: Optional authoritative managed-agent identifier
- `--auth`: Optional auth override for the resolved preset
- `--session-name`: Optional tmux session name (auto-generated if omitted)
- `--headless`: Launch in detached mode
- `--workdir`: Optional runtime working directory for the launched agent session

The command SHALL default the runtime workdir to the invocation cwd when `--workdir` is omitted.

The command SHALL NOT expose `--working-directory` as part of the current public launch surface.

The command SHALL NOT expose a separate CLI workspace-trust bypass flag on this surface.

The command SHALL proceed without a Houmao-managed workspace trust confirmation prompt before local launch begins.

The effective provider startup posture SHALL remain determined by the resolved preset `launch.prompt_mode` together with the downstream runtime/provider launch-policy contract.

#### Scenario: Operator specifies a custom session name

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --session-name my-agent`
- **THEN** the tmux session is created with the name `my-agent`

#### Scenario: Operator overrides preset auth

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --auth kimi-coding`
- **AND WHEN** the resolved preset would otherwise use a different default auth selection
- **THEN** the launch uses auth bundle `kimi-coding`
- **AND THEN** the built manifest records `kimi-coding` as the effective auth selection

#### Scenario: Operator supplies an explicit managed-agent name

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a`
- **THEN** the launch uses `worker-a` as the managed-agent logical name
- **AND THEN** the preset does not need to define any default managed-agent name

#### Scenario: Operator supplies an explicit runtime workdir
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --workdir /workspace/app`
- **THEN** the launched session uses `/workspace/app` as its runtime workdir
- **AND THEN** the manifest records `/workspace/app` as the launched agent working directory

#### Scenario: Local launch does not require a separate workspace-trust bypass flag

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **THEN** the command proceeds without a Houmao-managed workspace trust confirmation prompt
- **AND THEN** any no-prompt or full-autonomy startup posture comes from the resolved `launch.prompt_mode` rather than from a separate `--yolo` flag

### Requirement: `houmao-mgr agents launch` resolves preset selectors with explicit default-setup behavior

`houmao-mgr agents launch` SHALL support exactly two preset selector forms on `--agents`:

- bare role selector `<role>`, resolved together with the provider-derived tool to the unique named preset whose `role=<role>`, `tool=<tool>`, and `setup=default`
- explicit preset file path

The command SHALL NOT interpret `<role>/<setup>` as selector shorthand in this change.

When a bare role selector is used, the command SHALL resolve the selector against the parsed catalog for the invocation launch source context.

When an explicit preset file path is used, the command SHALL resolve that preset path directly and SHALL derive the launch source context from the resolved preset owner tree rather than from `--workdir`.

#### Scenario: Bare role selector resolves the default setup through a named preset

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **THEN** the command SHALL resolve the unique preset whose content declares `role: gpu-kernel-coder`, `tool: claude`, and `setup: default`
- **AND THEN** the resolved preset file SHALL live under `agents/presets/`

#### Scenario: Explicit preset path selects a non-default setup

- **WHEN** an operator runs `houmao-mgr agents launch --agents agents/presets/gpu-kernel-coder-codex-yunwu-openai.yaml --provider codex`
- **THEN** the command SHALL resolve that explicit preset file path directly

#### Scenario: Explicit preset path does not let `--workdir` retarget source resolution
- **WHEN** an operator runs `houmao-mgr agents launch --agents /source-repo/.houmao/agents/presets/gpu-kernel-coder-codex-yunwu-openai.yaml --provider codex --workdir /workspace/app`
- **THEN** the command SHALL resolve that explicit preset file path directly
- **AND THEN** it SHALL continue resolving source-project launch context from `/source-repo`
- **AND THEN** it SHALL NOT reinterpret `/workspace/app` as the source preset catalog location

#### Scenario: Hybrid role-setup shorthand is rejected

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder/research --provider claude_code`
- **THEN** the command SHALL NOT reinterpret that selector as `<role>/<setup>`
- **AND THEN** it SHALL fail clearly unless that input resolves as an explicit preset file path
