# Spec Delta

## ADDED Requirements

### Requirement: README links to managed agent memory guidance

The README SHALL link to maintained memory documentation for managed agents.

#### Scenario: Reader Seeks Managed Agent Memory Commands
- **WHEN** a reader needs to inspect memory paths, work with memo files, or resolve page paths
- **THEN** the linked documentation shows the supported scoped memory commands

## MODIFIED Requirements

### Requirement: README section ordering follows specialist-first onboarding

The README SHALL present an agent-first onboarding order: title/intro, Motivation, audience list, What It Is (with name origin), Why This Design, Architecture at a Glance, Quick Start, agent-driven examples, Core Concepts, Agent Loops, concise System Skills summary, Subsystems, Demos and Examples, CLI Entry Points, Full Documentation, Development, License.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The former Typical Use Cases section is removed; audience signposting in the "who this is for" list and the Agent Loops and Demos sections carry that content.

The Quick Start SHALL NOT require a reader to walk through a numbered 0-through-6 manual `houmao-mgr` tutorial before seeing Houmao's agent-driven value. Manual command details and secondary paths SHALL be linked to docs rather than expanded as the primary README flow.

#### Scenario: Reader scans the README headings
- **WHEN** a reader opens README.md and scans section headings
- **THEN** they see a concise Quick Start before detailed usage references
- **AND THEN** they see agent-driven examples before low-level CLI command details
- **AND THEN** the README does not present project init, specialist creation, managed launch, and full recipes as a long numbered manual tutorial

### Requirement: README leaves command detail to docs

The README SHALL keep command examples short and illustrative. Detailed command flags, full lifecycle command lists, complete system-skill catalogs, managed-header details, and recipe/launch-dossier reference material SHALL be linked to existing docs or reference pages instead of expanded inline.

#### Scenario: Reader wants command details
- **WHEN** a reader wants exact CLI syntax beyond the concise README examples
- **THEN** the README points them to the relevant getting-started or reference docs
- **AND THEN** the README itself remains focused on concepts, agent-driven workflows, and examples

## REMOVED Requirements

### Requirement: agents join is a secondary path (step 4)
**Reason**: Manual provider-session adoption is retired.
**Migration**: The Quickstart links to managed project launch.

### Requirement: agents join capabilities table mentions agents memory
**Reason**: The provider-session adoption table is retired.
**Migration**: Managed-agent memory guidance remains available through the README's documentation links.
