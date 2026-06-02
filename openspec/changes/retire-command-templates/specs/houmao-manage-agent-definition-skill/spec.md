## MODIFIED Requirements

### Requirement: `houmao-agent-definition` uses config drafts for supported config authoring flows
The packaged `houmao-agent-definition` skill SHALL instruct agents to use `houmao-mgr internals config-drafts generate` before authoring supported project configuration documents for these skill subcommands:

- `specialists`
- `profiles`
- `launch-dossiers`
- profile preparation inside `create-agent-fast-forward`

For those supported config-authoring flows, the skill SHALL tell agents to generate drafts from explicit user inputs and recovered explicit context only.

The skill SHALL NOT own full default-bearing YAML examples or command skeletons in Markdown for config shapes covered by `internals config-drafts`.

The skill SHALL describe config drafts as minimal opinionated drafts and SHALL direct full customization beyond the draft's required holes back to maintained project subcommands.

The skill SHALL direct agents to the CLI-owned config draft as the authoritative source for the config kind, fixed lane/source values, required credential/auth reference, and draft YAML shape.

For executable command-oriented workflows that are not config documents, the skill SHALL document direct `houmao-mgr` command snippets in fenced `bash` blocks and SHALL NOT call `houmao-mgr internals command-templates`.

#### Scenario: Profile authoring generates a config draft
- **WHEN** a user asks `houmao-agent-definition profiles` to create project profile `reviewer-fast` for specialist `reviewer` and credential `reviewer-creds`
- **AND WHEN** the user does not request prompt-mode or headless posture persistence
- **THEN** the skill guidance directs the agent to generate `project.profile` with only `name`, `specialist`, and `credential`
- **AND THEN** the generated draft records project-profile lane and specialist source without adding prompt-mode or headless defaults

#### Scenario: Launch dossier authoring generates a raw launch-profile draft
- **WHEN** a user asks `houmao-agent-definition launch-dossiers` to prepare raw launch profile `alice` with recipe `reviewer-codex` and credential `reviewer-creds`
- **THEN** the skill guidance directs the agent to generate `internals.native-agent.launch-dossier`
- **AND THEN** the generated draft records only the fixed recipe-backed profile values and required credential/auth reference

#### Scenario: Specialist authoring generates a specialist draft
- **WHEN** a user asks `houmao-agent-definition specialists` to prepare a Codex specialist named `reviewer` with credential `reviewer-creds`
- **THEN** the skill guidance directs the agent to generate `project.specialist`
- **AND THEN** the guidance does not require loading a separate executable-command schema to see every possible credential, skill, mailbox, and launch option

#### Scenario: Recipe authoring uses direct commands
- **WHEN** a user asks `houmao-agent-definition recipes` to create recipe `reviewer-codex` from role `reviewer` and tool `codex`
- **AND WHEN** no recipe config-draft contract exists
- **THEN** the skill guidance shows the maintained direct `houmao-mgr internals native-agent recipes ...` command in a fenced `bash` block
- **AND THEN** the guidance does not invent a recipe YAML draft that Houmao does not provide

#### Scenario: Fast-forward uses drafts and direct launch command printing
- **WHEN** `create-agent-fast-forward` prepares a launchable project profile and prints the launch command
- **THEN** the skill guidance uses config drafts for specialist/profile preparation
- **AND THEN** it prints the maintained `houmao-mgr project agents launch ...` command directly

## REMOVED Requirements

### Requirement: `houmao-agent-definition` delegates credential command shapes to credential templates
**Reason**: Credential command templates are retired with the command-template renderer.
**Migration**: Route credential authoring to `houmao-credential-mgr` or show direct maintained credential commands when the workflow is simple and explicit.

#### Scenario: Credential authoring does not use templates
- **WHEN** `houmao-agent-definition` needs credential discovery or mutation
- **THEN** it uses direct credential commands or delegates to the credential-management skill

### Requirement: `houmao-agent-definition` preserves prompt-mode and TUI/headless omission through templates
**Reason**: Prompt-mode and launch-posture omission is preserved through direct command guidance after command-template removal.
**Migration**: Omit prompt-mode and launch-posture flags from direct command snippets unless the user explicitly requests them or the selected tool/lane requires them.

#### Scenario: Omission remains direct
- **WHEN** a user does not specify prompt mode or launch posture
- **THEN** the skill omits those optional flags from the direct command snippet

## ADDED Requirements

### Requirement: `houmao-agent-definition` uses direct command snippets for executable workflows
The packaged `houmao-agent-definition` skill SHALL document executable commands as fenced `bash` snippets.

The skill SHALL NOT reference `houmao-mgr internals command-templates show`, `houmao-mgr internals command-templates render`, command-template ids, or command-template blocker recovery.

The skill SHALL preserve required-input and conflict guardrails in prose before each direct command workflow.

#### Scenario: Low-level role command is shown directly
- **WHEN** a user asks the skill to initialize or edit a low-level role
- **THEN** the skill guidance shows a direct `houmao-mgr internals native-agent roles ...` command in a fenced `bash` block
- **AND THEN** it does not render a command-template id first

#### Scenario: Launch command is shown directly
- **WHEN** a user asks the skill to print or run a managed launch command
- **THEN** the skill guidance shows a direct `houmao-mgr project agents launch ...` command in a fenced `bash` block
- **AND THEN** omitted optional flags remain absent unless explicitly requested
