## ADDED Requirements

### Requirement: `houmao-agent-definition` uses CLI-owned command templates for supported authoring flows
The packaged `houmao-agent-definition` skill SHALL instruct agents to use `houmao-mgr internals command-templates show|render` before authoring supported default-sensitive commands for these skill subcommands:

- `specialists`
- `profiles`
- `roles`
- `recipes`
- `raw-profiles`
- `create-agent-fast-forward`
- `launch-agent`

For those supported flows, the skill SHALL tell agents to render sparse intent from explicit user inputs and recovered explicit context only.

The skill SHALL NOT own full default-bearing command templates in Markdown for covered create, set, or launch commands.

The skill MAY summarize critical omission rules, but it SHALL direct agents to the CLI-owned template output as the authoritative source for required fields, optional fields, conflicts, clear flags, and omit-vs-set semantics.

#### Scenario: Profile authoring renders sparse intent before execution
- **WHEN** a user asks `houmao-agent-definition profiles` to create easy profile `reviewer-fast` for specialist `reviewer`
- **AND WHEN** the user does not request prompt-mode or headless posture persistence
- **THEN** the skill guidance directs the agent to render `project.easy.profile.create` with only the explicit profile and specialist fields
- **AND THEN** the guidance does not tell the agent to add `--prompt-mode unattended` or `--headless`

#### Scenario: Raw profile authoring uses raw-profile template
- **WHEN** a user asks `houmao-agent-definition raw-profiles` to update raw launch profile `alice` with workdir `/repos/alice-next`
- **THEN** the skill guidance directs the agent to render `project.agents.launch-profiles.set`
- **AND THEN** the guidance treats omitted mailbox, prompt overlay, managed-header, prompt-mode, and launch posture fields as preserved by the patch command

#### Scenario: Recipe authoring uses recipe template
- **WHEN** a user asks `houmao-agent-definition recipes` to create recipe `reviewer-codex` from role `reviewer` and tool `codex`
- **AND WHEN** the user does not request prompt-mode persistence
- **THEN** the skill guidance directs the agent to render `project.agents.recipes.add` with only the explicit recipe, role, and tool fields
- **AND THEN** the guidance does not tell the agent to add `--prompt-mode unattended`

#### Scenario: Role authoring uses role template
- **WHEN** a user asks `houmao-agent-definition roles` to update role `reviewer` with a new prompt file
- **THEN** the skill guidance directs the agent to render `project.agents.roles.set`
- **AND THEN** omitted prompt clear fields remain absent from the rendered intent

#### Scenario: Fast-forward launch command uses template output
- **WHEN** `create-agent-fast-forward` prepares a launchable easy profile and prints the launch command
- **THEN** the skill guidance directs the agent to base the printed launch command on `internals command-templates render`
- **AND THEN** it does not synthesize a launch command from a stale Markdown skeleton

### Requirement: `houmao-agent-definition` delegates credential command shapes to credential templates
When `houmao-agent-definition` needs to route credential discovery or credential creation while preparing specialists or recipes, it SHALL use CLI-owned credential command templates or direct read-only credential commands rather than carrying tool-specific credential option menus in agent-definition Markdown.

The skill MAY describe when credential discovery is needed, but credential command shape, project-vs-plain lane selection, and Claude/Codex/Gemini option fields SHALL come from the credential command-template registry or the credential-management skill.

#### Scenario: Specialist create references credential template for credential authoring
- **WHEN** a user asks `houmao-agent-definition specialists` to create a Codex specialist and also provide new credential material
- **THEN** the skill guidance routes credential command authoring through the matching credential template
- **AND THEN** the specialist command render only references the selected credential name

### Requirement: `houmao-agent-definition` preserves prompt-mode and TUI/headless omission through templates
The packaged `houmao-agent-definition` skill SHALL preserve the distinction between prompt mode and launch posture by following the CLI-owned template renderer for supported authoring flows.

When prompt mode is not explicit in the current prompt or recent conversation context, the skill SHALL omit prompt-mode fields from rendered intent rather than setting `unattended` or `as_is`.

When TUI/headless posture is not explicit and the selected tool or launch lane does not require headless posture, the skill SHALL omit launch-posture fields from rendered intent.

#### Scenario: Unspecified prompt mode remains unset
- **WHEN** a user asks the skill to create or update a Codex easy profile
- **AND WHEN** the user does not mention prompt mode
- **THEN** the rendered intent omits prompt mode
- **AND THEN** the resulting command does not persist a prompt-mode field only because the skill has a preferred default

#### Scenario: Explicit unattended is still honored
- **WHEN** a user explicitly asks the skill to make a profile launch with unattended prompt mode
- **THEN** the rendered intent includes prompt mode `unattended`
- **AND THEN** the resulting command includes the matching prompt-mode option reported by the template renderer

#### Scenario: Unspecified launch posture remains TUI-preferred
- **WHEN** a user asks the skill to prepare a launch command for a TUI-capable Codex or Claude profile
- **AND WHEN** the user does not request headless execution
- **THEN** the rendered intent omits headless launch posture
- **AND THEN** the resulting command remains TUI/local-interactive preferred where supported
