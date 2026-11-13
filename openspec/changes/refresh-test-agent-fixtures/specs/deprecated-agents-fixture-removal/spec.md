# Spec Delta

## MODIFIED Requirements

### Requirement: Repository SHALL not retain the deprecated `tests/fixtures/agents/` path as a tracked fixture surface

The repository SHALL NOT restore `tests/fixtures/agents/` as a live root, redirect, or compatibility alias. Maintained guidance SHALL point to plain seed assets, generic launch descriptors, the external local credential store, or owned external generated trees. Historical archived material MAY retain factual old paths, but maintained workflows SHALL NOT resolve live credentials from repository-local auth fixtures.

#### Scenario: Maintainer inspects the tracked fixture tree after removal
- **WHEN** a maintainer inspects tracked fixture assets and their guidance
- **THEN** the deprecated broad fixture root remains absent
- **AND THEN** guidance points to `tests/fixtures/plain-agent-def/`, `tests/fixtures/agent-launch/`, external local credentials, and owned private run trees according to purpose

#### Scenario: Maintained guidance does not reintroduce the deprecated path
- **WHEN** a maintainer reads maintained docs, specs, or runnable demo guidance
- **THEN** it does not instruct operators to use `tests/fixtures/agents/` or populate repository-local live auth fixtures
- **AND THEN** archived surfaces remain historical rather than acquiring compatibility aliases

#### Scenario: Existing ignored credentials survive fixture retirement
- **WHEN** tracked account-specific placeholder directories and guidance are retired
- **THEN** implementation preserves ignore coverage for any remaining local credential files
- **AND THEN** it does not automatically delete, move, or stage those files
