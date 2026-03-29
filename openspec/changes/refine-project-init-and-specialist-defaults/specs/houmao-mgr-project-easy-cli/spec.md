## MODIFIED Requirements

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
