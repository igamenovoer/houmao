## REMOVED Requirements

### Requirement: `houmao-agent-definition` uses CLI-owned command templates for supported authoring flows
**Reason**: Pre-launch project configuration authoring is moving to concise model-generated config drafts so agents do not need to load full command-template schemas for ordinary specialist/profile/raw-profile work.

**Migration**: Use `houmao-mgr internals config-drafts generate` for specialist, easy-profile, and raw launch-profile config-document authoring. Continue using `houmao-mgr internals command-templates render` for remaining command-oriented role, recipe, and launch-command workflows until those workflows gain a config-draft contract.

## ADDED Requirements

### Requirement: `houmao-agent-definition` uses config drafts for supported config authoring flows
The packaged `houmao-agent-definition` skill SHALL instruct agents to use `houmao-mgr internals config-drafts generate` before authoring supported project configuration documents for these skill subcommands:

- `specialists`
- `profiles`
- `raw-profiles`
- profile preparation inside `create-agent-fast-forward`

For those supported config-authoring flows, the skill SHALL tell agents to generate drafts from explicit user inputs and recovered explicit context only.

The skill SHALL NOT own full default-bearing YAML examples or command skeletons in Markdown for config shapes covered by `internals config-drafts`.

The skill MAY summarize critical omission rules, but it SHALL direct agents to the CLI-owned config draft as the authoritative source for the config kind, fixed lane/source values, explicit defaults, and draft YAML shape.

The skill MAY continue to use `houmao-mgr internals command-templates render` for command-oriented workflows such as `roles`, `recipes`, launch command printing, and remaining executable command construction.

#### Scenario: Profile authoring generates a config draft
- **WHEN** a user asks `houmao-agent-definition profiles` to create easy profile `reviewer-fast` for specialist `reviewer`
- **AND WHEN** the user does not request prompt-mode or headless posture persistence
- **THEN** the skill guidance directs the agent to generate `project.easy.profile` with only the explicit profile and specialist fields
- **AND THEN** the generated draft records easy-profile lane and specialist source without adding prompt-mode or headless defaults

#### Scenario: Raw profile authoring generates a raw launch-profile draft
- **WHEN** a user asks `houmao-agent-definition raw-profiles` to prepare raw launch profile `alice` with workdir `/repos/alice-next`
- **THEN** the skill guidance directs the agent to generate `project.agents.launch-profile`
- **AND THEN** the generated draft records only the explicit recipe-backed profile values and launch defaults supplied by the user

#### Scenario: Specialist authoring generates a specialist draft
- **WHEN** a user asks `houmao-agent-definition specialists` to prepare a Codex specialist named `reviewer`
- **THEN** the skill guidance directs the agent to generate `project.easy.specialist`
- **AND THEN** the guidance does not require loading the full `project.easy.specialist.create` command-template schema to see every possible credential, skill, mailbox, and launch option

#### Scenario: Recipe authoring can still use command templates
- **WHEN** a user asks `houmao-agent-definition recipes` to create recipe `reviewer-codex` from role `reviewer` and tool `codex`
- **AND WHEN** no recipe config-draft contract exists
- **THEN** the skill guidance may direct the agent to render `project.agents.recipes.add`
- **AND THEN** the guidance does not invent a recipe YAML draft that Houmao does not provide

#### Scenario: Fast-forward uses drafts for config and command templates for launch printing
- **WHEN** `create-agent-fast-forward` prepares a launchable easy profile and prints the launch command
- **THEN** the skill guidance uses config drafts for specialist/profile preparation
- **AND THEN** it may still base the printed launch command on `internals command-templates render`
