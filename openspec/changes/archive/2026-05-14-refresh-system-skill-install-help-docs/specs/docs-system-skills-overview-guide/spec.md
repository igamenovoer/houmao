## ADDED Requirements

### Requirement: System-skills overview explains installation choices

The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL explain the two supported documentation-facing installation choices for packaged Houmao system skills.

The guide SHALL recommend `npx skills add https://github.com/igamenovoer/houmao/tree/main/src/houmao/agents/assets/system_skills/` when `npx` and internet access are available, and SHALL state that the command points at the GitHub main-branch system-skill collection so the user can choose the packaged skill or skills to install.

The guide SHALL describe `houmao-mgr system-skills install` as the Houmao-owned path for installed-package/offline use, project-local or explicit homes, named sets, subset skills, symlink/copy projection, and retired-skill cleanup.

The guide SHALL continue to explain managed launch and join auto-install behavior separately from explicit user-driven installation.

#### Scenario: Reader chooses between install paths
- **WHEN** a reader opens the system-skills overview to learn how to install skills
- **THEN** the guide presents the `npx skills add` path for `npx` plus internet environments
- **AND THEN** it presents `houmao-mgr system-skills install` for offline, package-local, explicit-home, named-set, subset, symlink/copy, or cleanup needs
- **AND THEN** it keeps managed auto-install behavior separate from explicit install choices

### Requirement: System-skills overview explains prompt-level help

The getting-started guide `docs/getting-started/system-skills-overview.md` SHALL explain that every current packaged Houmao system skill supports explicit read-only help from its top-level skill instructions.

The guide SHALL include one or more examples such as `$houmao-touring help`, `$houmao-agent-email-comms help`, or `usage for houmao-agent-definition`.

The guide SHALL explain that explicit help or usage requests are handled before normal workflow routing, while ordinary task requests such as "help me send mail" still route to the task workflow.

#### Scenario: Reader learns the skill help convention
- **WHEN** a reader opens the system-skills overview guide
- **THEN** they see prompt-level help examples for installed skills
- **AND THEN** they understand help is read-only and handled before workflow routing
- **AND THEN** they understand ordinary task-shaped requests continue into the task workflow
