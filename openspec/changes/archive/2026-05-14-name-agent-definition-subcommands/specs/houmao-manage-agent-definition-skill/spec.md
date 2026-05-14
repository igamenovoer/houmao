## MODIFIED Requirements

### Requirement: `houmao-agent-definition` is the canonical pre-launch agent-definition skill
The packaged `houmao-agent-definition` skill SHALL be the canonical Houmao-owned skill for persisted pre-launch agent definition workflows.

That unified skill SHALL expose these skill-level subcommands:

- `roles` for low-level prompt-only roles;
- `recipes` for low-level recipes, with `presets` as a compatibility alias;
- `raw-profiles` for low-level recipe-backed launch profiles using the underlying `houmao-mgr project agents launch-profiles ...` CLI;
- `specialists` for project-easy specialist templates;
- `profiles` for specialist-backed easy profiles;
- `create-agent-fast-forward` for creating or selecting a specialist, creating or updating an easy profile, printing the launch command, and not launching a live agent;
- `launch-agent` for the limited easy launch entry point that hands off broader live lifecycle work to `houmao-agent-instance`;
- `stop-agent` for the limited easy stop entry point that hands off broader live lifecycle work to `houmao-agent-instance`.

The skill SHALL treat loosely stated `profile`, `agent profile`, `launch profile`, and `ready profile` wording as the `profiles` subcommand by default unless the user explicitly asks for `raw-profiles`, raw profile behavior, recipe-backed profile behavior, or the exact `project agents launch-profiles` CLI surface.

#### Scenario: Unified skill routes named subcommands
- **WHEN** an agent reads the packaged `houmao-agent-definition` skill
- **THEN** the top-level page lists the supported skill subcommands and their local subskill routes
- **AND THEN** the agent can route a user request that explicitly names `profiles`, `raw-profiles`, or `create-agent-fast-forward` without asking which branch was intended

#### Scenario: Ambiguous launch profile means easy profile
- **WHEN** a user asks to create or update an agent launch profile without saying raw, recipe-backed, or `project agents launch-profiles`
- **THEN** the skill routes the request to the `profiles` subcommand
- **AND THEN** it does not route the request to low-level recipe-backed launch profiles by default

### Requirement: `houmao-agent-definition` uses lane-specific subskills
The unified `houmao-agent-definition` skill SHALL keep its entry page concise and SHALL route detailed behavior into lane-specific local subskills or references.

At minimum, the skill SHALL distinguish `roles`, `recipes`, `raw-profiles`, `specialists`, `profiles`, `create-agent-fast-forward`, `launch-agent`, and `stop-agent`.

The skill SHALL include shared guidance for launcher resolution, missing-input handling, profile-lane terminology, and credential-routing boundaries.

The entry page SHALL either route existing generic `actions/*` pages through the new subcommand vocabulary or mark those pages as legacy low-level-only references so they do not conflict with the subcommand table.

#### Scenario: Entry page loads only the relevant lane
- **WHEN** the user asks to update one easy profile
- **THEN** `houmao-agent-definition` routes to the `profiles` subcommand and easy-profile subskill
- **AND THEN** it does not load or flatten unrelated low-level recipe, raw-profile, or easy-instance launch instructions into the entry page

#### Scenario: Raw profile route is explicit
- **WHEN** the user asks for `raw-profiles` or for the exact `project agents launch-profiles` surface
- **THEN** `houmao-agent-definition` routes to the low-level recipe-backed profile subskill
- **AND THEN** the subskill names the underlying `houmao-mgr project agents launch-profiles ...` commands
