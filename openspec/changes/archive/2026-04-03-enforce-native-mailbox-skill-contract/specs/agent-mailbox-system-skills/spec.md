## ADDED Requirements

### Requirement: Runtime-owned mailbox system skills are never copied into launched project content
Runtime-owned Houmao mailbox system skills SHALL remain runtime-home assets under the active tool skill destination and SHALL NOT be copied into copied project worktrees, generated demo project content, or other launched project content merely to make ordinary mailbox prompting succeed.

Maintained runtime and demo workflows SHALL treat project content and runtime-owned mailbox skills as separate surfaces:
- copied project content remains ordinary work content,
- runtime-owned mailbox skills remain installed in the tool-native runtime-home skill destination,
- ordinary mailbox prompting relies on the installed runtime-home skill surface rather than on copied project-local mailbox skill mirrors.

#### Scenario: Supported demo prepares a copied project for a mailbox-enabled session
- **WHEN** a maintained demo prepares a copied project worktree for a mailbox-enabled Claude, Codex, or Gemini session
- **THEN** the copied project does not receive Houmao runtime-owned mailbox skills as project content
- **AND THEN** the mailbox skill set remains available only through the tool-native runtime-home skill destination

#### Scenario: Runtime-owned mailbox skills remain separate from copied work content
- **WHEN** an agent session includes both copied project files and runtime-owned mailbox skills
- **THEN** the agent can use the installed mailbox skills without requiring a `project/skills` or worktree-local mailbox mirror
- **AND THEN** success of ordinary mailbox prompting does not depend on copied project-local `SKILL.md` files
