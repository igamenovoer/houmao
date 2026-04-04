# demo-agent-launch-recovery Specification

## Purpose
Define the launch-recovery boundary after the current demo and tutorial packs were archived as historical reference.

## Requirements

### Requirement: Archived demos SHALL NOT define current launch-recovery obligations

The active system contract SHALL NOT require maintainers to repair or preserve archived workflows under `scripts/demo/legacy/` as part of current launch-recovery work.

Archived demo and tutorial materials MAY preserve historical launch wiring, field names, or path references for reference, but supported launch-recovery work SHALL focus only on live non-archived workflows and canonical preset-backed fixture surfaces.

#### Scenario: Live launch recovery excludes archived demo workflows

- **WHEN** a maintainer evaluates whether a launch failure blocks the current supported system contract
- **AND WHEN** that failure belongs only to archived material under `scripts/demo/legacy/`
- **THEN** that failure does not create a current launch-recovery obligation for the supported live system
