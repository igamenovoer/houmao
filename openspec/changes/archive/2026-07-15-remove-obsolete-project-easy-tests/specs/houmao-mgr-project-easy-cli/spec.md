## ADDED Requirements

### Requirement: Maintained tests target promoted project commands

Maintained tests for specialist, profile, and project-managed-agent behavior SHALL describe and exercise the supported `project specialist`, `project profile`, and `project agents` command groups. A maintained test SHALL NOT assert that a `project easy ...` command succeeds or is the expected command shape.

Tests MAY name or inspect internal implementation modules that retain `easy` terminology when isolation requires an implementation-targeted patch, but they SHALL NOT present those module names as public CLI paths.

#### Scenario: Obsolete successful command-shape test is absent

- **WHEN** the maintained test suite is searched for expected successful `project easy ...` command vectors
- **THEN** no such test remains
- **AND THEN** tests of the corresponding supported behavior use promoted project command terminology

#### Scenario: Retirement remains covered negatively

- **WHEN** CLI-shape tests inspect the public `project` command group
- **THEN** they verify that `easy` is not registered
- **AND THEN** they verify that `specialist`, `profile`, and `agents` are registered
