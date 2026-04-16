## ADDED Requirements

### Requirement: README system-skills table lists the LLM Wiki utility skill
The README "System Skills: Agent Self-Management" subsection SHALL document `houmao-utils-llm-wiki` as one of the packaged Houmao-owned system skills.

The README row SHALL describe the skill as an explicit utility for persistent Markdown LLM Wiki knowledge bases, including scaffold, ingest, compile, query, lint, audit, and local viewer workflows.

The README SHALL explain that `houmao-utils-llm-wiki` is not part of managed-home auto-install or CLI-default install selections and must be selected with `--skill-set utils` or `--skill houmao-utils-llm-wiki`.

#### Scenario: Reader sees the LLM Wiki utility in the README catalog
- **WHEN** a reader scans the README system-skills table
- **THEN** they find `houmao-utils-llm-wiki`
- **AND THEN** the row describes persistent Markdown knowledge-base workflows

#### Scenario: Reader sees explicit utility install examples
- **WHEN** a reader scans the README system-skills install examples
- **THEN** they can find an example using `--skill-set utils` or `--skill houmao-utils-llm-wiki`
- **AND THEN** the README does not imply that the utility skill is installed by default
