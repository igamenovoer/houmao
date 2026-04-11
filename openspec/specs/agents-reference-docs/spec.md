# agents-reference-docs Specification

## Purpose

**RETIRED.** This capability previously defined the structure, coverage, and quality bar for runtime-managed agent reference documentation published under `docs/reference/agents/`. That dedicated subtree has been retired because the April 2026 project-overlay and launch-profile refactors redistributed the same material across `docs/reference/run-phase/`, `docs/reference/system-files/`, and `docs/reference/cli/`, where it now lives under successor capability specs.

Successor coverage:

- Lifecycle, backend, and procedural guidance now belong to `docs-run-phase-reference` (see `docs/reference/run-phase/session-lifecycle.md`, `docs/reference/run-phase/backends.md`, and related pages).
- Runtime-owned filesystem layout, manifest persistence, discovery publication, and cleanup boundaries now belong to `system-files-reference-docs` (see `docs/reference/system-files/index.md` and `docs/reference/system-files/agents-and-runtime.md`).
- Public CLI surface coverage now belongs to `docs-cli-reference` (see `docs/reference/cli/houmao-mgr.md`, `docs/reference/cli/agents-gateway.md`, and `docs/reference/cli/agents-mail.md`).
- Project-aware resolution guidance now lives at `docs/reference/system-files/project-aware-operations.md` under `docs-project-aware-operations`.

This spec intentionally retains no functional requirements; it exists only to record the retirement and direct readers to the successor specs.

## Requirements

### Requirement: Retired agents reference docs SHALL defer to successor specs
This capability SHALL remain retired and SHALL direct documentation guarantees to the successor specs listed in the Purpose section.

#### Scenario: Reader finds successor coverage
- **WHEN** a maintainer inspects the retired `agents-reference-docs` capability
- **THEN** the spec identifies that active requirements live in successor documentation capabilities
- **AND THEN** the retired capability does not define duplicate runtime-managed agent reference requirements
