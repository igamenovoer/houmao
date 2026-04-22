# houmao-mgr-agents-launch Specification

## Purpose
Define the local `houmao-mgr agents launch` contract for brain construction and runtime startup without requiring `houmao-server`.
## Requirements
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

### Requirement: `houmao-mgr agents launch` supports unified model configuration
`houmao-mgr agents launch` SHALL accept optional `--model <name>` as a one-off launch-time model override.

`houmao-mgr agents launch` SHALL also accept optional `--reasoning-level <integer>=non-negative` as a one-off launch-time tool/model-specific reasoning preset index.

Those unified launch-owned overrides SHALL be supported for both direct recipe-backed launch through `--agents` and explicit launch-profile-backed launch through `--launch-profile`.

When `--model` or `--reasoning-level` is omitted, the effective launch-owned value for that subfield MAY still come from the resolved recipe, the resolved launch profile, or a lower-precedence copied tool-native default.

Direct `--model` and `--reasoning-level` SHALL override recipe-owned and launch-profile-owned defaults without rewriting those stored reusable sources.

The launch surface SHALL NOT impose a portable `1..10` reasoning cap. Model-aware saturation or rejection semantics are handled later by the shared model-selection resolution path.

#### Scenario: Direct recipe-backed launch uses the stored source model when no override is supplied
- **WHEN** recipe `gpu-kernel-coder-codex-default` stores `launch.model: gpt-5.4`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex`
- **THEN** the resulting launch uses model `gpt-5.4`

#### Scenario: Launch-profile-backed launch uses the stored profile model when no direct override is supplied
- **WHEN** launch profile `alice` stores model override `gpt-5.4-mini`
- **AND WHEN** its source recipe stores `launch.model: gpt-5.4`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice`
- **THEN** the resulting launch uses model `gpt-5.4-mini`

#### Scenario: Direct `--model` wins over the launch-profile default
- **WHEN** launch profile `alice` stores model override `gpt-5.4-mini`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --model gpt-5.4-nano`
- **THEN** the resulting launch uses model `gpt-5.4-nano`
- **AND THEN** the stored launch profile still records `gpt-5.4-mini` as its reusable default

#### Scenario: Direct `--reasoning-level` wins over the launch-profile default
- **WHEN** launch profile `alice` stores reasoning override `2`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --reasoning-level 12`
- **THEN** the resulting launch uses launch-owned reasoning preset index `12`
- **AND THEN** the stored launch profile still records `2` as its reusable default

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

### Requirement: `houmao-mgr agents launch` supports headless and interactive modes

`houmao-mgr agents launch` SHALL support both headless (detached) and interactive (tmux-backed TUI) modes.

When `--headless` is specified, the agent SHALL run as a detached headless process.

When `--headless` is not specified, the agent SHALL start the selected provider's interactive terminal UI in a tmux session.

When `--headless` is not specified and the caller provides a usable interactive terminal, the CLI SHALL perform the operator handoff to that tmux session through the repo-owned tmux integration boundary rather than through an ad hoc raw tmux subprocess call.

When `--headless` is not specified and the caller does not provide a usable interactive terminal, the command SHALL still be considered successful once the runtime session is live and the provider reaches the required ready posture, SHALL NOT attempt a terminal attach that can fail solely because the caller is non-interactive, and SHALL surface enough tmux identity for a later manual attach.

Interactive or non-interactive launch SHALL still fail if the session falls back to an idle shell before the provider reaches its interactive ready posture.

#### Scenario: Headless launch runs detached

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **THEN** the agent starts in a tmux-backed headless session without attaching the operator's terminal
- **AND THEN** the command prints the agent identity and manifest path, then exits

#### Scenario: Interactive launch attaches to a live provider TUI when the caller is interactive

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the caller has a usable interactive terminal
- **THEN** the agent starts the provider's interactive terminal UI in a tmux session
- **AND THEN** the CLI attaches the operator's terminal to that tmux session through the repo-owned tmux integration path
- **AND THEN** the launch is not considered successful if the session falls back to an idle shell before the provider reaches its interactive ready posture

#### Scenario: Non-interactive caller does not turn a successful launch into a false attach failure

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the caller has no usable interactive terminal
- **THEN** the agent still starts the provider's interactive terminal UI in a tmux session
- **AND THEN** the command reports launch success without attempting a tmux attach that would fail only because the caller is non-interactive
- **AND THEN** the output still surfaces the tmux session identity needed for a later manual attach

### Requirement: `houmao-mgr agents launch` resolves backend from provider and launch mode

`houmao-mgr agents launch` SHALL resolve the runtime launch surface from the provider identifier together with whether `--headless` was requested.

At minimum:

- headless `claude_code` launch uses the `claude_headless` backend
- headless `codex` launch uses the `codex_headless` backend
- headless `gemini_cli` launch uses the `gemini_headless` backend
- non-headless launch uses a local interactive runtime surface rather than a detached headless backend

#### Scenario: Headless Claude launch resolves to `claude_headless`

- **WHEN** an operator runs `houmao-mgr agents launch --provider claude_code --agents gpu-kernel-coder --headless`
- **THEN** the agent is launched using the `claude_headless` backend

#### Scenario: Interactive Claude launch does not reuse the headless transport

- **WHEN** an operator runs `houmao-mgr agents launch --provider claude_code --agents gpu-kernel-coder` without `--headless`
- **THEN** the agent is launched on the local interactive runtime surface
- **AND THEN** the session is treated as TUI transport rather than headless transport

#### Scenario: Unsupported provider is rejected

- **WHEN** an operator runs `houmao-mgr agents launch --provider unsupported_tool --agents gpu-kernel-coder`
- **THEN** the command fails with a clear error listing the supported providers

### Requirement: `houmao-mgr agents launch` reports unattended strategy compatibility failures distinctly

When local `houmao-mgr agents launch` requests launch settings that must be resolved before provider startup, the command SHALL report launch-policy compatibility failures distinctly from backend-selection failures and post-start provider-runtime failures.

#### Scenario: Interactive Claude launch reports unattended version gap before provider startup

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code` without `--headless`
- **AND WHEN** the selected preset resolves to unattended launch policy, whether explicitly through `launch.prompt_mode: unattended` or implicitly through the unattended default
- **AND WHEN** no compatible Claude strategy exists for the detected version on the local interactive launch surface
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and local interactive launch surface
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the tmux-attached TUI became ready

#### Scenario: Headless Claude launch reports unattended version gap before provider startup

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --headless`
- **AND WHEN** the selected preset resolves to unattended launch policy, whether explicitly through `launch.prompt_mode: unattended` or implicitly through the unattended default
- **AND WHEN** no compatible Claude strategy exists for the detected version on the `claude_headless` backend
- **THEN** the command fails before Claude Code starts
- **AND THEN** the error identifies the requested unattended policy, detected Claude version, and `claude_headless` backend
- **AND THEN** the error makes clear that launch-mode selection succeeded but provider startup was blocked before the detached headless runtime session became live

### Requirement: `houmao-mgr agents launch` preserves preset launch settings during local build

When `houmao-mgr agents launch` resolves a native preset-backed target from the canonical parsed catalog, it SHALL preserve the preset's requested launch settings when building the brain manifest for local startup.

At minimum, preset `launch.prompt_mode` and preset `launch.overrides` SHALL be forwarded into brain construction so the built manifest and subsequent runtime launch use the same requested launch posture and overrides.

For `launch.prompt_mode`, the effective preserved values SHALL use the `unattended|as_is` policy vocabulary, and preset omission SHALL resolve to unattended before manifest write.

#### Scenario: Omitted prompt mode defaults to unattended during local `agents launch`

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** the selected preset omits `launch.prompt_mode`
- **THEN** the local brain build records unattended operator-prompt intent in the built brain manifest
- **AND THEN** the local runtime launch uses that unattended intent for the selected launch surface

#### Scenario: Explicit as-is policy survives local `agents launch`

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** the selected preset requests `launch.prompt_mode: as_is`
- **THEN** the local brain build records `as_is` operator-prompt intent in the built brain manifest
- **AND THEN** the local runtime launch leaves provider startup behavior untouched for the selected launch surface

#### Scenario: Preset launch overrides survive local `agents launch`

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex`
- **AND WHEN** the selected preset requests `launch.overrides.tool_params`
- **THEN** the local brain build records the equivalent launch overrides in the built manifest
- **AND THEN** the local runtime launch uses those preserved overrides for the selected tool

### Requirement: `houmao-mgr agents launch` keeps managed-agent identity launch-time only

Preset-backed launch SHALL NOT depend on preset-owned default managed-agent names. `--agent-name` and `--agent-id` SHALL remain optional launch-time inputs.

When `--agent-name` is omitted, the runtime SHALL derive the fallback managed-agent logical name from tool plus role using the existing runtime auto-name path. Operators who need multiple distinct concurrently managed logical agents from the same preset SHALL provide explicit `--agent-name` values.

#### Scenario: Launch succeeds without an explicit managed-agent name

- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code`
- **AND WHEN** the preset does not define any managed-agent name
- **THEN** the runtime SHALL derive the logical managed-agent name from the resolved tool and role
- **AND THEN** the launch SHALL succeed without requiring any preset-owned identity field

### Requirement: `houmao-mgr agents launch` supports explicit launch-profile-backed launch
`houmao-mgr agents launch` SHALL support selecting a reusable explicit launch profile through `--launch-profile <name>`.

`--launch-profile` and `--agents` SHALL be mutually exclusive.

When `--launch-profile` is used, the command SHALL:
- resolve the named explicit launch profile from the selected source project context,
- resolve the profile's referenced recipe source,
- derive the effective recipe and tool from that source before build,
- apply launch-profile defaults before direct CLI overrides.

`houmao-mgr agents launch` SHALL NOT consume easy `project easy profile` selections through `--launch-profile`.

When the resolved profile source already determines one exact tool family, the effective provider SHALL default from that resolved source.

If the operator supplies `--provider` together with `--launch-profile`, the system SHALL either accept the value when it matches the resolved profile source or fail clearly when it conflicts.

#### Scenario: Launch-profile-backed launch derives provider from the resolved recipe
- **WHEN** launch profile `alice` resolves to one Codex-backed recipe source
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice`
- **THEN** the command derives the effective provider from that resolved source
- **AND THEN** the operator does not need to restate the provider only to launch the stored profile

#### Scenario: Launch-profile selector conflicts with direct source selector
- **WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --agents gpu-kernel-coder`
- **THEN** the command fails clearly before build
- **AND THEN** it reports that `--launch-profile` and `--agents` cannot be combined

### Requirement: Launch-profile-backed launch applies profile defaults before direct CLI overrides
When `houmao-mgr agents launch` resolves an explicit launch profile, the effective launch or build specification SHALL be composed from:

1. source recipe defaults
2. launch-profile defaults
3. direct CLI overrides

At minimum, launch-profile-backed launch SHALL allow profile defaults to contribute:
- managed-agent name or id
- working directory
- auth override
- operator prompt-mode override
- durable env defaults
- declarative mailbox config

Direct CLI overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` SHALL remain one-off overrides and SHALL NOT rewrite the stored launch profile.

#### Scenario: Launch-profile-backed launch uses stored managed-agent name when none is supplied
- **WHEN** launch profile `alice` stores default managed-agent name `alice`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice`
- **THEN** the launch uses `alice` as the managed-agent logical name
- **AND THEN** the operator does not need to restate that name for each launch from the same profile

#### Scenario: Direct auth override wins over the launch-profile default
- **WHEN** launch profile `alice` stores auth override `alice-creds`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --auth breakglass`
- **THEN** the launch uses auth bundle `breakglass`
- **AND THEN** the stored launch profile still records `alice-creds` as its reusable default

#### Scenario: Distinct concurrent logical agents require explicit names

- **WHEN** an operator needs two distinct concurrently managed logical agents from the same preset
- **THEN** the operator SHALL provide distinct `--agent-name` values for those launches
- **AND THEN** the system SHALL treat those explicit names, not the preset path, as the distinguishing logical identities

### Requirement: `houmao-mgr agents launch` consumes the canonical parsed contract

`houmao-mgr agents launch` SHALL consume canonical parsed definitions or one derived resolved launch specification rather than reading user-facing source files directly inside downstream launch and build stages.

#### Scenario: Source-layout parsing stays upstream of launch and build

- **WHEN** `houmao-mgr agents launch` handles one operator request
- **THEN** any source-layout-specific parsing SHALL happen before downstream launch and build logic consumes the resolved inputs
- **AND THEN** builder and runtime stages SHALL operate on canonical parsed data rather than on raw source mappings

### Requirement: `houmao-mgr agents launch` accepts user-specified agent identity fields

`houmao-mgr agents launch` SHALL accept optional managed-agent identity inputs for launch-time publication.

At minimum:

- `--agent-name <name>` MAY be supplied
- `--agent-id <id>` MAY be supplied

When the caller omits `--agent-name`, the launch path SHALL allow runtime identity derivation from the resolved tool and role using the existing runtime auto-name path.

When the caller omits `--agent-id` and an effective managed-agent name exists, the launch path SHALL derive the effective authoritative identity as `md5(agent_name).hexdigest()`.

The launch path SHALL validate explicit `agent_name` and `agent_id` values against the shared registry's filesystem-safe and URL-safe identity rules before publishing the live record.

#### Scenario: Launch accepts explicit friendly name and authoritative id

- **WHEN** an operator runs `houmao-mgr agents launch --agents projection-demo --provider codex --agent-name gpu --agent-id gpu-prod-001 --yolo`
- **THEN** the launch path publishes the managed agent with friendly name `gpu` and authoritative id `gpu-prod-001`
- **AND THEN** later exact control may target that agent by `--agent-id gpu-prod-001`

#### Scenario: Launch derives authoritative id when omitted

- **WHEN** an operator runs `houmao-mgr agents launch --agents projection-demo --provider codex --agent-name gpu --yolo`
- **THEN** the launch path derives the effective authoritative identity as `md5("gpu").hexdigest()`
- **AND THEN** the published live record uses that derived value as `agent_id`

### Requirement: `houmao-mgr agents launch` reports managed-agent and tmux identities separately

When `houmao-mgr agents launch` completes successfully, the command SHALL report the managed-agent identity fields separately from the tmux session handle used to host the live terminal surface.

At minimum, the successful launch output SHALL surface:

- the effective `agent_name` for later `houmao-mgr agents ...` commands
- the authoritative `agent_id`
- the actual `tmux_session_name`
- the `manifest_path`

When the operator supplied `--session-name`, that value SHALL remain the tmux session handle only unless it independently matches the chosen managed-agent name by coincidence. The launch output SHALL make that distinction visible to the operator.

When the operator did not supply `agent_id`, the launch path SHALL surface the effective derived `agent_id` used for publication and later exact addressing.

#### Scenario: Interactive launch prints control ref and tmux session distinctly

- **WHEN** an operator runs `houmao-mgr agents launch --agents projection-demo --provider codex --session-name hm-gw-track-codex --yolo`
- **THEN** the successful launch output includes the effective `agent_name`, the authoritative `agent_id`, the tmux session name `hm-gw-track-codex`, and the manifest path
- **AND THEN** the output makes clear which value to use for later managed-agent commands versus tmux attach operations

#### Scenario: Custom session name does not redefine the managed-agent ref

- **WHEN** an operator launches a managed agent with `--session-name my-custom-tmux-name`
- **AND WHEN** the runtime publishes a different managed-agent name in the shared registry
- **THEN** the launch output shows both values distinctly
- **AND THEN** `my-custom-tmux-name` is not implied to have replaced the managed-agent name

#### Scenario: Omitted agent id reports the derived effective identity

- **WHEN** an operator launches a managed agent without supplying `agent_id`
- **THEN** the launch output includes the effective `agent_id = md5(agent_name).hexdigest()`
- **AND THEN** the operator can use that derived `agent_id` for later exact disambiguation if needed

### Requirement: `houmao-mgr agents launch` supports one-shot managed-header override
`houmao-mgr agents launch` SHALL accept one-shot managed-header override flags:

- `--managed-header`
- `--no-managed-header`

Those flags SHALL be mutually exclusive.

When neither flag is supplied, `agents launch` SHALL inherit managed-header policy from the selected launch profile when one is present, otherwise from the system default.

Direct one-shot managed-header override SHALL influence only the current launch and SHALL NOT rewrite stored launch-profile state.

#### Scenario: Direct launch disables the managed header for one launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --no-managed-header`
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** future launches without `--no-managed-header` still fall back to profile or system-default behavior

#### Scenario: Direct disable wins over launch-profile-owned enabled policy
- **WHEN** launch profile `alice` stores managed-header policy `enabled`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --no-managed-header`
- **THEN** the resulting managed launch does not prepend the managed prompt header
- **AND THEN** stored launch profile `alice` still records managed-header policy `enabled`

#### Scenario: Direct enable wins over launch-profile-owned disabled policy
- **WHEN** launch profile `alice` stores managed-header policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --managed-header`
- **THEN** the resulting managed launch prepends the managed prompt header
- **AND THEN** stored launch profile `alice` still records managed-header policy `disabled`

### Requirement: `houmao-mgr agents launch` supports launch-owned managed force takeover

`houmao-mgr agents launch` SHALL accept optional `--force` for replacing an existing fresh live owner of the resolved managed identity on the current launch.

`--force` MAY be supplied bare or with an explicit mode value.

Bare `--force` SHALL default to mode `keep-stale`.

The only supported explicit force mode values SHALL be `keep-stale` and `clean`.

The selected force mode SHALL remain launch-owned only and SHALL NOT be persisted into reusable launch profiles.

When no force mode is supplied and a fresh live session already owns the resolved managed identity, the command SHALL fail rather than replacing that live owner.

When `--force` is supplied and a fresh live session already owns the resolved managed identity, the command SHALL delegate to the managed runtime takeover flow for that identity.

The command SHALL target takeover by the resolved managed identity rather than by tmux session name alone.

#### Scenario: Bare `--force` defaults to `keep-stale`
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a --force`
- **AND WHEN** a fresh live session already owns managed identity `worker-a`
- **THEN** the launch requests managed takeover in mode `keep-stale`
- **AND THEN** the command does not require the operator to spell `keep-stale` explicitly

#### Scenario: Explicit `clean` selects destructive takeover for the current launch only
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a --force clean`
- **AND WHEN** a fresh live session already owns managed identity `worker-a`
- **THEN** the launch requests managed takeover in mode `clean`
- **AND THEN** that `clean` selection applies only to the current launch invocation

#### Scenario: Force mode does not rewrite launch profile defaults
- **WHEN** launch profile `alice` exists
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --force clean`
- **THEN** the current launch uses managed takeover mode `clean`
- **AND THEN** stored launch profile `alice` remains unchanged and does not gain a persisted force mode

#### Scenario: Missing `--force` preserves the existing ownership conflict failure
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a`
- **AND WHEN** a fresh live session already owns managed identity `worker-a`
- **THEN** the command fails rather than replacing that existing live owner

#### Scenario: Tmux session-name collision alone does not authorize takeover
- **WHEN** an unrelated live session already uses tmux session name `my-agent`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --agent-name worker-a --session-name my-agent --force`
- **AND WHEN** that unrelated live session does not own managed identity `worker-a`
- **THEN** the command does not treat `--force` as permission to replace that unrelated session
- **AND THEN** the launch still fails on the tmux session-name collision

### Requirement: `houmao-mgr agents launch` supports one-shot launch-owned system-prompt appendix
`houmao-mgr agents launch` SHALL accept optional launch-owned system-prompt appendix input through:

- `--append-system-prompt-text`
- `--append-system-prompt-file`

Those options SHALL be mutually exclusive.

When either option is supplied, the provided appendix SHALL participate only in the current launch's effective prompt composition and SHALL NOT rewrite the source role prompt or any stored launch profile.

When the launch also resolves a launch-profile prompt overlay, the appendix SHALL be appended after overlay resolution within the current launch's effective prompt composition.

#### Scenario: Direct managed launch appends one-shot prompt text for the current launch only
- **WHEN** an operator runs `houmao-mgr agents launch --agents researcher --provider codex --append-system-prompt-text "Prefer the current branch naming rules."`
- **THEN** the current launch's effective prompt includes a launch appendix after the other resolved prompt-body sections
- **AND THEN** a later launch without the appendix option does not inherit that one-shot appendix

#### Scenario: Profile-backed launch appends file-based appendix after overlay resolution
- **WHEN** launch profile `alice` already contributes a prompt overlay
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --append-system-prompt-file /tmp/appendix.md`
- **THEN** the current launch appends the file content after the resolved launch-profile overlay
- **AND THEN** stored launch profile `alice` remains unchanged

#### Scenario: Launch rejects conflicting appendix inputs
- **WHEN** an operator supplies both `--append-system-prompt-text` and `--append-system-prompt-file` on the same `houmao-mgr agents launch` invocation
- **THEN** the command fails clearly before brain construction begins
- **AND THEN** it does not start a managed session for that invalid launch request

### Requirement: `houmao-mgr agents launch` supports one-shot managed-header section overrides
`houmao-mgr agents launch` SHALL accept repeatable one-shot managed-header section overrides using `--managed-header-section SECTION=STATE`.

Supported `SECTION` values SHALL include:

- `identity`
- `houmao-runtime-guidance`
- `automation-notice`
- `task-reminder`
- `mail-ack`

Supported `STATE` values SHALL include:

- `enabled`
- `disabled`

When neither `--managed-header-section` nor whole-header `--managed-header` / `--no-managed-header` is supplied, `agents launch` SHALL inherit managed-header section policy from the selected launch profile when one is present, otherwise from the section default.

Direct one-shot managed-header section overrides SHALL influence only the current launch and SHALL NOT rewrite stored launch-profile state.

If the whole managed header resolves to disabled, section-level overrides SHALL NOT render managed-header sections for that launch.

#### Scenario: Direct launch disables only automation notice for one launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --managed-header-section automation-notice=disabled`
- **THEN** the resulting managed launch keeps the managed header enabled
- **AND THEN** the resulting managed launch includes the identity and Houmao runtime guidance sections
- **AND THEN** the resulting managed launch does not include the automation notice section

#### Scenario: Direct section override does not rewrite launch profile
- **WHEN** launch profile `alice` stores automation notice section policy `disabled`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --managed-header-section automation-notice=enabled`
- **THEN** the resulting managed launch includes the automation notice section
- **AND THEN** stored launch profile `alice` still records automation notice section policy `disabled`

#### Scenario: Direct launch enables mail acknowledgement for one launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --managed-header-section mail-ack=enabled`
- **THEN** the resulting managed launch keeps the managed header enabled
- **AND THEN** the resulting managed launch includes the mail acknowledgement section
- **AND THEN** the resulting managed launch does not rewrite stored launch-profile state

#### Scenario: Whole-header disable still wins over direct section enable
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --no-managed-header --managed-header-section automation-notice=enabled`
- **THEN** the resulting managed launch does not include `<managed_header>`
- **AND THEN** the automation notice section does not render

#### Scenario: Invalid section override fails before launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider claude_code --managed-header-section typo=enabled`
- **THEN** the command fails before provider launch
- **AND THEN** the error identifies `typo` as an unsupported managed-header section name

### Requirement: `houmao-mgr agents launch` reports simplified managed memory paths
`houmao-mgr agents launch` SHALL create and report memory root, memo file, and pages directory for tmux-backed managed sessions.

The command SHALL NOT accept `--persist-dir` or `--no-persist-dir`.

When project context supplies the default memory root, the root SHALL derive from the selected source overlay rather than from `--workdir`.

Launch completion output SHALL NOT report scratch directory, persist binding, or persist directory as current memory fields.

#### Scenario: Project-context launch derives memory root from the source overlay
- **WHEN** an active project overlay resolves as `/repo-a/.houmao`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --workdir /repo-b`
- **THEN** the resulting managed launch resolves memory root under `/repo-a/.houmao/memory/agents/<agent-id>/`
- **AND THEN** it does not derive the default memory root from `/repo-b`

#### Scenario: Persist flags are not supported on launch
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --no-persist-dir`
- **THEN** the command fails before provider launch
- **AND THEN** the error identifies `--no-persist-dir` as unsupported

### Requirement: Explicit launch-profile-backed launch applies stored memo seeds
`houmao-mgr agents launch --launch-profile <name>` SHALL apply the selected explicit launch profile's memo seed as part of the managed launch when that profile stores a memo seed.

The memo seed SHALL be applied after explicit launch-profile resolution and direct override resolution for managed-agent identity, so the seed targets the same authoritative agent id used by the launched runtime.

Direct launch-time overrides for other launch fields, such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir`, SHALL remain one-shot overrides and SHALL NOT rewrite the stored memo seed.

#### Scenario: Explicit launch profile seeds memo for overridden agent name
- **WHEN** explicit launch profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-default --agent-name reviewer-a`
- **THEN** Houmao applies the memo seed to the memo paths for managed agent `reviewer-a`
- **AND THEN** the stored launch profile remains unchanged

#### Scenario: Explicit launch profile launch reports memo seed result
- **WHEN** explicit launch profile `reviewer-default` stores a memo seed
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-default`
- **THEN** the launch completion payload reports the memo seed application result
- **AND THEN** the launch completion payload does not report a memo seed policy

### Requirement: Explicit launch-profile memo seed application is component-scoped
`houmao-mgr agents launch --launch-profile <name>` SHALL apply the selected explicit launch profile's memo seed using source-scoped replacement semantics from managed launch runtime.

Direct launch-time overrides for other launch fields, such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir`, SHALL remain one-shot overrides and SHALL NOT rewrite the stored memo seed or its component scope.

#### Scenario: Explicit memo-only launch preserves pages
- **WHEN** explicit launch profile `reviewer-default` stores memo-only seed text
- **AND WHEN** managed agent `reviewer-default` already has pages
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-default`
- **THEN** Houmao replaces only the launched agent's `houmao-memo.md`
- **AND THEN** it leaves the launched agent's pages unchanged
- **AND THEN** the launch completion payload reports the memo seed application result

#### Scenario: Explicit pages-only launch preserves memo
- **WHEN** explicit launch profile `reviewer-default` stores a directory memo seed containing `pages/notes/start.md` and no `houmao-memo.md`
- **AND WHEN** managed agent `reviewer-default` already has a memo
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile reviewer-default`
- **THEN** Houmao replaces only the launched agent's contained pages
- **AND THEN** it leaves the launched agent's `houmao-memo.md` unchanged

### Requirement: `houmao-mgr agents launch` supports explicit preserved-home reuse

`houmao-mgr agents launch` SHALL accept optional `--reuse-home` for the current launch.

`--reuse-home` SHALL be launch-owned only and SHALL NOT be persisted into explicit launch profiles.

When `--reuse-home` is supplied, the command SHALL treat the request as restart of one stopped logical managed agent on one compatible preserved home for the resolved managed identity instead of allocating a new home.

The command SHALL support `--reuse-home` for both direct `--agents` launch and explicit `--launch-profile` launch.

For explicit `--launch-profile` launch, reused-home restart SHALL apply the currently stored launch-profile inputs, together with any stronger direct CLI overrides, onto the preserved home before startup. Updating the stored launch profile after the prior run SHALL therefore affect the restarted agent even though the prior stopped instance was not mutated in place.

The command SHALL require the prior runtime to already be down and its tmux session to already be absent. `--reuse-home` SHALL NOT by itself replace a fresh live owner of the same managed identity.

When the stopped lifecycle metadata carries a prior tmux session name and the operator does not provide `--session-name`, the command SHALL request restart using that same tmux session name.

When `--session-name` is provided, that explicit override SHALL take precedence over the stopped record's prior tmux session name.

The command SHALL use the stopped local lifecycle record and preserved manifest/home metadata as restart authority and SHALL NOT require separate registry cleanup before restarting.

If no compatible stopped preserved home can be resolved, the command SHALL fail clearly and SHALL NOT silently launch on a new home.

#### Scenario: Launch-profile-backed launch restarts one stopped preserved home with updated profile inputs
- **WHEN** explicit launch profile `alice` resolves managed identity `alice`
- **AND WHEN** a stopped compatible preserved home exists for `alice` with prior tmux session name `HOUMAO-alice-1700000000000`
- **AND WHEN** the stored launch profile `alice` has been updated since the prior run
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --reuse-home`
- **THEN** the command requests reused-home restart for managed identity `alice`
- **AND THEN** the current stored launch-profile inputs are projected onto the preserved home before startup
- **AND THEN** the restart does not require separate registry cleanup
- **AND THEN** the restart requests tmux session name `HOUMAO-alice-1700000000000` by default

#### Scenario: Direct launch rejects reuse-home when no preserved home exists
- **WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --agent-name reviewer --reuse-home`
- **AND WHEN** no compatible stopped preserved home exists for managed identity `reviewer`
- **THEN** the command fails clearly
- **AND THEN** it does not silently start a fresh-home launch

#### Scenario: Reuse-home does not bypass live-owner conflict on its own
- **WHEN** a fresh live session already owns managed identity `reviewer`
- **AND WHEN** an operator runs `houmao-mgr agents launch --agents gpu-kernel-coder --provider codex --agent-name reviewer --reuse-home`
- **THEN** the command fails rather than replacing that live owner
- **AND THEN** the failure tells the operator to stop the live owner before attempting reused-home restart

#### Scenario: Explicit session-name override wins over the stopped record
- **WHEN** explicit launch profile `alice` resolves one stopped compatible preserved home
- **AND WHEN** the stopped lifecycle metadata carries prior tmux session name `HOUMAO-alice-1700000000000`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --reuse-home --session-name alice-restart-debug`
- **THEN** the command requests reused-home restart on the preserved home
- **AND THEN** the restart uses tmux session name `alice-restart-debug`
- **AND THEN** it does not silently force the old tmux session name when the operator supplied a stronger override
