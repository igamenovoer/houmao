# houmao-mgr-project-easy-cli Specification

## Purpose
Define the higher-level `houmao-mgr project easy` workflow for compiling reusable specialist definitions into the canonical repo-local `.houmao/agents/` tree.

## Requirements

### Requirement: `project easy specialist create` compiles one specialist into canonical project agent artifacts

`houmao-mgr project easy specialist create` SHALL create one project-local specialist by compiling the operator's inputs into the canonical `.houmao/agents/` tree.

At minimum, `specialist create` SHALL require:

- `--name <specialist>`
- `--tool <claude|codex|gemini>`

At minimum, `specialist create` SHALL support:

- zero or one system prompt source from `--system-prompt <text>` or `--system-prompt-file <path>`
- optional `--credential <name>`
- common credential inputs `--api-key` and `--base-url`
- a tool-specific auth-file flag appropriate to the selected tool
- repeated `--with-skill <skill-dir>`

When `--credential` is omitted, the command SHALL derive the credential bundle name as `<specialist-name>-creds`.

When no system prompt source is provided, the command SHALL still materialize the canonical role prompt path and SHALL treat that role as having no system prompt.

The command SHALL compile one specialist into:

- `.houmao/agents/roles/<specialist>/system-prompt.md`
- `.houmao/agents/roles/<specialist>/presets/<tool>/default.yaml`
- `.houmao/agents/tools/<tool>/auth/<resolved-credential>/...`
- copied skill directories under `.houmao/agents/skills/<skill>/...`
- metadata under `.houmao/easy/specialists/<specialist>.toml`

If the resolved auth bundle already exists and no new auth inputs are provided, the command SHALL reuse that bundle.

If the resolved auth bundle does not exist and no auth inputs are provided, the command SHALL fail clearly.

The resulting project-local `.houmao/agents/` tree SHALL remain the authoritative build and launch input.

#### Scenario: Create uses the derived credential name by default
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --system-prompt "You are a precise repo researcher." --tool codex --api-key sk-test --with-skill /tmp/notes-skill`
- **THEN** the command writes `.houmao/agents/roles/researcher/system-prompt.md`
- **AND THEN** it writes `.houmao/agents/roles/researcher/presets/codex/default.yaml`
- **AND THEN** it writes `.houmao/agents/tools/codex/auth/researcher-creds/` using the selected credential inputs
- **AND THEN** it copies the selected skill into `.houmao/agents/skills/`

#### Scenario: Gemini specialist creation records the Gemini lane
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --system-prompt-file /tmp/reviewer.md --tool gemini --credential vertex --gemini-oauth-creds /tmp/oauth.json`
- **THEN** the command writes a preset under `.houmao/agents/roles/reviewer/presets/gemini/default.yaml`
- **AND THEN** the specialist metadata records that later launch must derive the Gemini provider lane from that tool selection

#### Scenario: Promptless specialist still compiles to the canonical role tree
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --tool gemini --gemini-oauth-creds /tmp/oauth.json`
- **THEN** the command writes `.houmao/agents/roles/reviewer/system-prompt.md`
- **AND THEN** that canonical prompt file may be empty
- **AND THEN** it writes a preset under `.houmao/agents/roles/reviewer/presets/gemini/default.yaml`
- **AND THEN** the specialist metadata records that later launch must derive the Gemini provider lane from that tool selection

#### Scenario: Derived credential bundle is reused when already present
- **WHEN** `.houmao/agents/tools/codex/auth/researcher-creds/` already exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --system-prompt "You are a precise repo researcher."`
- **THEN** the command reuses `researcher-creds`
- **AND THEN** it does not fail only because `--credential` was omitted

#### Scenario: Missing derived credential without auth input fails clearly
- **WHEN** `.houmao/agents/tools/codex/auth/researcher-creds/` does not exist
- **AND WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --tool codex --system-prompt "You are a precise repo researcher."`
- **THEN** the command fails clearly
- **AND THEN** the error identifies the resolved credential name `researcher-creds`

### Requirement: `project easy specialist list/get/remove` manages persisted specialist definitions

`houmao-mgr project easy specialist list` SHALL enumerate persisted specialist definitions under `.houmao/easy/specialists/`.

`houmao-mgr project easy specialist get --name <specialist>` SHALL report one specialist's high-level metadata plus the generated canonical paths.

`houmao-mgr project easy specialist remove --name <specialist>` SHALL remove the persisted specialist metadata and the generated role subtree for that specialist.

`specialist remove` SHALL NOT delete shared skills or shared auth bundles automatically only because one specialist referenced them.

#### Scenario: Get reports both metadata and generated paths
- **WHEN** `.houmao/easy/specialists/researcher.toml` exists
- **AND WHEN** an operator runs `houmao-mgr project easy specialist get --name researcher`
- **THEN** the command reports the specialist's tool, credential, and skill selections
- **AND THEN** it reports the generated role prompt, preset, and auth paths

#### Scenario: Remove preserves shared auth and skill artifacts
- **WHEN** specialist `researcher` and another specialist both reference skill `notes` and auth bundle `work`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist remove --name researcher`
- **THEN** the command removes the persisted `researcher` specialist metadata and role subtree
- **AND THEN** it does not delete the shared `notes` skill or `work` auth bundle only because `researcher` was removed

### Requirement: `project easy instance launch` derives provider from one specialist and launches one runtime instance

`houmao-mgr project easy instance launch --specialist <specialist> --name <instance>` SHALL launch one managed agent by resolving the compiled specialist definition and delegating to the existing native managed-agent launch flow.

The launch provider SHALL be derived from the specialist's selected tool:

- `claude` -> `claude_code`
- `codex` -> `codex`
- `gemini` -> `gemini_cli`

The operator SHALL NOT need to provide the provider identifier separately when launching an instance from a specialist.

When launch-time mailbox association is requested, the command SHALL accept these high-level mailbox inputs:

- `--mail-transport <filesystem|email>`
- `--mail-root <dir>` when `--mail-transport filesystem`
- optional `--mail-account-dir <dir>` when `--mail-transport filesystem`

When `--mail-transport filesystem` is selected and `--mail-account-dir` is omitted, the command SHALL launch the instance with an in-root filesystem mailbox account for that instance's mailbox identity under the selected mailbox root.

When `--mail-transport filesystem` is selected and `--mail-account-dir` is provided, the command SHALL launch the instance with a symlink-backed filesystem mailbox account whose shared-root mailbox entry points at the requested mailbox account directory.

When `--mail-transport email` is selected in this change, the command SHALL fail clearly as not implemented and SHALL exit non-zero before creating a managed-agent session.

If mailbox validation or mailbox bootstrap fails during a mailbox-enabled easy launch, the command SHALL fail clearly and SHALL NOT report a successful managed-agent launch.

#### Scenario: Specialist launch derives the Codex provider automatically
- **WHEN** specialist `researcher` was created with tool `codex`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1`
- **THEN** the command launches the managed agent using the compiled `researcher` role and the derived `codex` provider
- **AND THEN** the operator does not need to pass `--provider codex` explicitly

#### Scenario: Filesystem easy launch binds an in-root mailbox account
- **WHEN** specialist `researcher` was created with tool `codex`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --mail-transport filesystem --mail-root /tmp/houmao-mail`
- **THEN** the command launches the managed agent successfully
- **AND THEN** the launched instance is associated with a filesystem mailbox account under the selected mailbox root for that instance identity

#### Scenario: Filesystem easy launch binds a symlink-backed private mailbox directory
- **WHEN** specialist `researcher` was created with tool `codex`
- **AND WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --mail-transport filesystem --mail-root /tmp/houmao-mail --mail-account-dir /tmp/private-mail/repo-research-1`
- **THEN** the command launches the managed agent successfully
- **AND THEN** the launched instance is associated with a symlink-backed filesystem mailbox account under `/tmp/houmao-mail`
- **AND THEN** the concrete mailbox account directory is `/tmp/private-mail/repo-research-1`

#### Scenario: Instance launch requires both specialist and instance identity
- **WHEN** an operator requests `project easy instance launch`
- **AND WHEN** the operator omits either `--specialist` or `--name`
- **THEN** the command fails clearly before launch
- **AND THEN** the error explains that instance launch requires both the specialist selector and the concrete instance identity

#### Scenario: Email transport fails fast before launch
- **WHEN** an operator runs `houmao-mgr project easy instance launch --specialist researcher --name repo-research-1 --mail-transport email`
- **THEN** the command exits non-zero
- **AND THEN** the error reports that the real-email easy-launch path is not implemented yet
- **AND THEN** no managed-agent session is created

### Requirement: `project easy instance list/get/stop` presents runtime state by specialist and wraps existing runtime stop control

`houmao-mgr project easy instance list` SHALL present launched managed agents as instances, annotated by their originating specialist when that specialist can be resolved.

`houmao-mgr project easy instance get --name <instance>` SHALL report the current managed-agent runtime summary plus the originating specialist metadata when available.

`houmao-mgr project easy instance stop --name <instance>` SHALL stop one managed-agent instance after verifying that the resolved runtime session belongs to the current project overlay.

`project easy instance stop` SHALL delegate to the existing canonical managed-agent stop implementation rather than directly killing the resolved tmux session.

This change SHALL NOT define `project easy instance stop` semantics that differ from the current managed-agent stop behavior.

The instance view SHALL be derived from existing managed-agent runtime state and SHALL NOT require a second persisted per-instance config contract in v1.

When the resolved runtime state includes a mailbox association, `project easy instance get` SHALL report the effective mailbox summary, including:

- the high-level mailbox transport,
- the mailbox address,
- the shared mailbox root,
- the mailbox kind,
- the resolved concrete mailbox directory.

`project easy instance list` SHALL surface whether each instance currently has a mailbox association and MAY present that information as a compact mailbox summary.

The `instance` group SHALL own launch, stop, and runtime inspection, while the `specialist` group remains limited to reusable configuration management.

#### Scenario: Instance list groups launched agents by specialist
- **WHEN** a launched managed agent was started from specialist `researcher`
- **AND WHEN** an operator runs `houmao-mgr project easy instance list`
- **THEN** the command reports that managed agent as an instance of `researcher`
- **AND THEN** the command derives that view from the existing runtime state rather than from a second stored instance definition

#### Scenario: Instance get reports the effective mailbox association
- **WHEN** launched instance `repo-research-1` was started with a filesystem mailbox association
- **AND WHEN** an operator runs `houmao-mgr project easy instance get --name repo-research-1`
- **THEN** the command reports the instance's runtime summary and originating specialist metadata
- **AND THEN** it also reports the effective mailbox transport, mailbox address, mailbox root, mailbox kind, and resolved mailbox directory from runtime-derived state

#### Scenario: Instance stop wraps the canonical managed-agent stop path
- **WHEN** launched instance `repo-research-1` belongs to the current project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy instance stop --name repo-research-1`
- **THEN** the command verifies that the resolved managed-agent manifest belongs to the discovered project overlay
- **AND THEN** it stops the instance by delegating to the existing managed-agent stop implementation rather than by directly killing tmux from the project CLI

#### Scenario: Instance stop rejects a managed agent outside the current project overlay
- **WHEN** managed agent `repo-research-1` resolves successfully
- **AND WHEN** its manifest does not belong to the discovered project overlay
- **AND WHEN** an operator runs `houmao-mgr project easy instance stop --name repo-research-1`
- **THEN** the command fails clearly
- **AND THEN** it does not delegate stop control for a managed agent outside the current project overlay
