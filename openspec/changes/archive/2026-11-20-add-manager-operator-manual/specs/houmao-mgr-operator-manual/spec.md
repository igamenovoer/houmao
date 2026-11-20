# Manager Operator Manual

## Purpose

Give agents concise guidance for operating Houmao through the installed manager CLI, including when Houmao system skills are unavailable.

## ADDED Requirements

### Requirement: The manager exposes an indexed operator manual

`houmao-mgr manual` SHALL print a task-oriented index. `houmao-mgr manual <catalog>` SHALL print the selected catalog index. `houmao-mgr manual <catalog> <page>` SHALL print exactly the selected page. The root and catalog indexes SHALL list the commands needed to reach every catalog and page directly below them.

#### Scenario: An agent finds a workflow from root help

- **WHEN** an agent runs `houmao-mgr --help` or bare `houmao-mgr`
- **THEN** root help identifies `houmao-mgr manual` as a source of operating guidance and includes the detailed documentation link
- **AND WHEN** the agent runs `houmao-mgr manual`, `houmao-mgr manual start`, and `houmao-mgr manual start first-agent`
- **THEN** those commands print the manual index, the `start` index, and the first-agent page respectively

#### Scenario: The manual uses ordinary command help and errors

- **WHEN** an agent requests `--help` at the manual, catalog, or page level
- **THEN** the CLI prints ordinary command help for that level
- **AND WHEN** the agent supplies an unknown catalog or page
- **THEN** the CLI returns a usage error without printing manual content

### Requirement: The installed manual reads standalone Markdown resources

The manager SHALL ship each index and page as a separate Markdown file in the distribution. The CLI SHALL load the selected file from its installed package. All manual prose, including index descriptions, SHALL reside in these files so editors can revise the prose independently of command registration.

#### Scenario: An agent reads the manual in an empty workspace

- **WHEN** an agent invokes a manual index or page from the installed release with an empty home and working directory, offline and without Houmao skills, project state, or a running agent or gateway
- **THEN** the CLI prints the packaged document
- **AND THEN** the command performs no project or runtime discovery, setup, or mutation and invokes no external command

#### Scenario: A registered document is missing from the installation

- **WHEN** the CLI cannot load the file for a valid manual command
- **THEN** it reports that the selected manual document is unavailable and exits unsuccessfully

### Requirement: Manual reads respect the manager output style

The manual SHALL honor the manager's root output-style selection. Plain output SHALL write Markdown directly to standard output. JSON SHALL contain a `path` array of command components beginning with `manual` and a `content` string containing the same Markdown. Fancy output SHALL present the same document content. The CLI SHALL print the result without opening a pager or requiring a terminal.

#### Scenario: An agent requests structured page output

- **WHEN** an agent runs `houmao-mgr --print-json manual operate turns`
- **THEN** the result contains `path` equal to `["manual", "operate", "turns"]` and the corresponding Markdown in `content`

### Requirement: Pages teach operating decisions and evidence

The manual SHALL provide concise, agent-facing workflows organized around user requests. Each page SHALL identify when it applies, which decisions or steps to take, and what evidence to check. It SHALL refer readers to command `--help` for syntax and to detailed reference material for deeper procedures and contracts.

#### Scenario: An operator agent prepares or launches a first worker

- **WHEN** an agent reads `manual start first-agent` or `manual start existing-project`
- **THEN** it can inspect the selected project, reuse existing setup, distinguish preparation from launch, and identify the launched worker by its returned ID

#### Scenario: A managed agent handles a notifier wakeup

- **WHEN** an agent reads `manual communicate wakeups`
- **THEN** it can distinguish stored mail from notification, preserve the supplied gateway, channel, and binding, and process one round with any required reply before archiving successful work

#### Scenario: An operator agent chooses team coordination

- **WHEN** an agent reads `manual coordinate team`, `manual coordinate workspaces`, or `manual coordinate loops`
- **THEN** it can distinguish an operator-run handoff from a recurring generated loop and find guidance for worker responsibilities, workspace isolation, and artifact evidence

### Requirement: The manual covers the core operator and managed-agent workflows

The first manual release SHALL include the five catalogs and their pages listed in the scenarios below. Catalog indexes SHALL describe the operator goal each page serves.

#### Scenario: The start catalog covers orientation and authority

- **WHEN** an agent opens `manual start`
- **THEN** the index lists `first-agent`, `existing-project`, and `targets`

#### Scenario: The prepare catalog covers launch preparation

- **WHEN** an agent opens `manual prepare`
- **THEN** the index lists `credentials`, `definitions`, and `launch`

#### Scenario: The operate catalog covers work and lifecycle

- **WHEN** an agent opens `manual operate`
- **THEN** the index lists `inspect`, `turns`, `lifecycle`, and `memory`

#### Scenario: The communicate catalog covers mail and gateway usage

- **WHEN** an agent opens `manual communicate`
- **THEN** the index lists `mail`, `mailboxes`, `gateway`, and `wakeups`

#### Scenario: The coordinate catalog covers team and loop decisions

- **WHEN** an agent opens `manual coordinate`
- **THEN** the index lists `team`, `workspaces`, and `loops`
