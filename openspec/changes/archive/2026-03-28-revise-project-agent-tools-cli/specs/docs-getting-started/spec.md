## ADDED Requirements

### Requirement: Getting-started docs use tool-oriented project auth commands
Repo-owned getting-started guidance for the repo-local `.houmao/` project overlay SHALL describe project-local auth management through `houmao-mgr project agent-tools <tool> auth ...` rather than through `project credential ...`.

At minimum, the agent-definition layout guide SHALL explain that the CLI mirrors `.houmao/agents/tools/<tool>/auth/<name>/`, and quickstart-style examples SHALL use the renamed command family when showing local auth-bundle creation or inspection.

#### Scenario: Reader sees matching CLI and directory-tree nouns
- **WHEN** a reader follows the project-overlay and agent-definition getting-started docs
- **THEN** the docs use `houmao-mgr project agent-tools <tool> auth ...` when describing local auth bundles
- **AND THEN** the surrounding explanation matches the documented directory tree under `.houmao/agents/tools/<tool>/auth/<name>/`
