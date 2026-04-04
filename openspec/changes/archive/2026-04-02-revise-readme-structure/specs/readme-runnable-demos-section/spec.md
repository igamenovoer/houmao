## ADDED Requirements

### Requirement: README includes a Runnable Demos section

The `README.md` SHALL include a section titled "Runnable Demos" that surfaces the two maintained runnable demos with brief descriptions and run commands. The section SHALL appear after the usage path sections.

#### Scenario: Reader finds both demos in README

- **WHEN** a reader scans the README
- **THEN** they find a "Runnable Demos" section listing `scripts/demo/minimal-agent-launch/` and `scripts/demo/single-agent-mail-wakeup/` with one-liner descriptions and representative run commands

### Requirement: Minimal agent launch demo entry describes the preset-based path

The minimal-agent-launch demo entry SHALL explain that it demonstrates the full preset-backed build → launch → prompt → stop cycle in headless mode with either Claude or Codex.

#### Scenario: Reader understands what the minimal demo covers

- **WHEN** a reader reads the minimal-agent-launch demo entry
- **THEN** they understand it shows the preset-based headless launch path
- **AND THEN** they find a run command like `scripts/demo/minimal-agent-launch/run_demo.sh`

### Requirement: Single agent mail wakeup demo entry describes the mailbox workflow

The single-agent-mail-wakeup demo entry SHALL explain that it demonstrates the easy-specialist + gateway + mailbox-notifier wake-up workflow with either Claude or Codex.

#### Scenario: Reader understands what the mail wakeup demo covers

- **WHEN** a reader reads the single-agent-mail-wakeup demo entry
- **THEN** they understand it shows project-easy specialist creation, gateway attach, mail-notifier polling, and agent wake-up on incoming mail
- **AND THEN** they find a run command and a link to the demo's own README for details
