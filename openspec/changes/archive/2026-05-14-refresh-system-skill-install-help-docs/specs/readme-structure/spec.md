## ADDED Requirements

### Requirement: Install prerequisites are step 0

The README Quick Start step 0 SHALL remain titled "Install & Prerequisites" or an equivalent install/prerequisite heading. It SHALL focus on installing Houmao itself and verifying host prerequisites such as `tmux`.

Step 0 SHALL NOT be the only place where system-skill installation is introduced. System-skill installation choices SHALL appear in the recommended agent-driven step.

#### Scenario: Reader sees Houmao install prerequisites first
- **WHEN** a reader scans the README Quick Start section
- **THEN** step 0 explains how to install Houmao and verify prerequisites
- **AND THEN** system-skill installation choices are handled in the recommended agent-driven step rather than being the sole purpose of step 0

## MODIFIED Requirements

### Requirement: Drive with Your CLI Agent is step 1

Step 1 SHALL be titled "Drive with Your CLI Agent (Recommended)" and SHALL present the skill-driven path as the primary recommended entry point. It SHALL instruct the user to install system skills, start their agent from the same directory, and invoke `houmao-touring`.

When `npx` is available and the target machine has internet access, step 1 SHALL recommend installing from the GitHub main-branch system-skill collection with:

```bash
npx skills add https://github.com/igamenovoer/houmao/tree/main/src/houmao/agents/assets/system_skills/
```

Step 1 SHALL present `houmao-mgr system-skills install --tool <tool>[,<tool>...]` as the Houmao-owned installation path for environments without `npx` or internet access, installed-package/offline workflows, named sets, subset skills, explicit homes, symlink/copy projection, or retired-skill cleanup.

Step 1 SHALL explain that omitted `--home` resolves each selected tool through its own env/default home rules, and that explicit `--home` is valid only for a single selected tool.

Step 1 SHALL mention that installed Houmao system skills support explicit read-only help such as `$houmao-touring help` or `$houmao-agent-email-comms help`.

Step 1 SHALL NOT present `--set` as the current named system-skill set selection flag.

A note SHALL state that the remaining steps show the manual CLI equivalents for reference.

#### Scenario: User follows step 1 with npx available
- **WHEN** a user reads step 1 on a machine with `npx` and internet access
- **THEN** they see the `npx skills add` command pointed at the GitHub main-branch `system_skills/` directory
- **AND THEN** they understand that the Skills CLI lets them choose which packaged skill or skills to install
- **AND THEN** they know to start their agent and invoke `houmao-touring`

#### Scenario: User follows step 1 without npx or with custom install needs
- **WHEN** a user reads step 1 without `npx`, without internet access, or with explicit selection or home needs
- **THEN** they see `houmao-mgr system-skills install --tool <tool>[,<tool>...]` as the supported Houmao-owned path
- **AND THEN** they understand omitted-home and single-tool explicit-home behavior

#### Scenario: User discovers read-only skill help from step 1
- **WHEN** a reader finishes the recommended agent-driven setup guidance
- **THEN** they see at least one explicit skill-help prompt example
- **AND THEN** the README describes help as read-only usage guidance before workflows

#### Scenario: Step 1 is clearly positioned as recommended
- **WHEN** a reader scans the Quick Start section headings
- **THEN** step 1 carries a "(Recommended)" qualifier that distinguishes it from the manual steps that follow

## REMOVED Requirements

### Requirement: system-skills install is step 0

**Reason**: System-skill installation now belongs in the recommended agent-driven step, where the docs can present both the external Skills CLI path and the Houmao-owned installer path.

**Migration**: Keep step 0 focused on installing Houmao and checking host prerequisites. Move system-skill installation guidance to step 1 and present `npx skills add` first when available, with `houmao-mgr system-skills install` as the offline/customizable path.
