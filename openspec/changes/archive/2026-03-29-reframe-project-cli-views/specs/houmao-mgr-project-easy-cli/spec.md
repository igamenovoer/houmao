## ADDED Requirements

### Requirement: `project easy specialist create` compiles one specialist into canonical project agent artifacts

`houmao-mgr project easy specialist create` SHALL create one project-local specialist by compiling the operator's inputs into the canonical `.houmao/agents/` tree.

At minimum, `specialist create` SHALL require:

- `--name <specialist>`
- exactly one of `--system-prompt <text>` or `--system-prompt-file <path>`
- `--tool <claude|codex|gemini>`
- `--credential <name>`

At minimum, `specialist create` SHALL support:

- common credential inputs `--api-key` and `--base-url`
- a tool-specific auth-file flag appropriate to the selected tool
- repeated `--with-skill <skill-dir>`

The command SHALL compile one specialist into:

- `.houmao/agents/roles/<specialist>/system-prompt.md`
- `.houmao/agents/roles/<specialist>/presets/<tool>/default.yaml`
- `.houmao/agents/tools/<tool>/auth/<credential>/...`
- copied skill directories under `.houmao/agents/skills/<skill>/...`
- metadata under `.houmao/easy/specialists/<specialist>.toml`

The resulting project-local `.houmao/agents/` tree SHALL remain the authoritative build and launch input.

#### Scenario: Create compiles one Codex specialist into the canonical tree
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name researcher --system-prompt "You are a precise repo researcher." --tool codex --credential work --api-key sk-test --with-skill /tmp/notes-skill`
- **THEN** the command writes `.houmao/agents/roles/researcher/system-prompt.md`
- **AND THEN** it writes `.houmao/agents/roles/researcher/presets/codex/default.yaml`
- **AND THEN** it writes `.houmao/agents/tools/codex/auth/work/` using the selected credential inputs
- **AND THEN** it copies the selected skill into `.houmao/agents/skills/`

#### Scenario: Gemini specialist creation records the Gemini lane
- **WHEN** an operator runs `houmao-mgr project easy specialist create --name reviewer --system-prompt-file /tmp/reviewer.md --tool gemini --credential vertex --gemini-oauth-creds /tmp/oauth.json`
- **THEN** the command writes a preset under `.houmao/agents/roles/reviewer/presets/gemini/default.yaml`
- **AND THEN** the specialist metadata records that later launch must derive the Gemini provider lane from that tool selection

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

### Requirement: `project easy specialist launch` derives provider and launches from the compiled specialist

`houmao-mgr project easy specialist launch --name <specialist>` SHALL launch one managed agent by resolving the compiled specialist definition and delegating to the existing native managed-agent launch flow.

The launch provider SHALL be derived from the specialist's selected tool:

- `claude` -> `claude_code`
- `codex` -> `codex`
- `gemini` -> `gemini_cli`

The operator SHALL NOT need to provide the provider identifier separately when launching a specialist.

#### Scenario: Specialist launch derives the Codex provider automatically
- **WHEN** specialist `researcher` was created with tool `codex`
- **AND WHEN** an operator runs `houmao-mgr project easy specialist launch --name researcher --instance repo-research-1`
- **THEN** the command launches the managed agent using the compiled `researcher` role and the derived `codex` provider
- **AND THEN** the operator does not need to pass `--provider codex` explicitly

### Requirement: `project easy instance list/get` presents runtime state by specialist

`houmao-mgr project easy instance list` SHALL present launched managed agents as instances, annotated by their originating specialist when that specialist can be resolved.

`houmao-mgr project easy instance get --name <instance>` SHALL report the current managed-agent runtime summary plus the originating specialist metadata when available.

The instance view SHALL be derived from existing managed-agent runtime state and SHALL NOT require a second persisted per-instance config contract in v1.

#### Scenario: Instance list groups launched agents by specialist
- **WHEN** a launched managed agent was started from specialist `researcher`
- **AND WHEN** an operator runs `houmao-mgr project easy instance list`
- **THEN** the command reports that managed agent as an instance of `researcher`
- **AND THEN** the command derives that view from the existing runtime state rather than from a second stored instance definition
