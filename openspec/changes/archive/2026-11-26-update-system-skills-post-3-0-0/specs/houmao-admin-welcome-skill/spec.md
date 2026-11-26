# Spec Delta

## ADDED Requirements

### Requirement: Admin welcome skill covers post-3.0.0 runtime concepts and tool surfaces
`houmao-admin-welcome` (`references/concepts.md` and `references/guided-paths.md`) SHALL cover DeepSeek Harness (`dsh`) adapter checks, run modes (`headless`, `service`, `tui`, `web`), `--executor` contexts, `houmao-mgr manual`, gateway dashboard and open-roster access, durable usage records, `houmao-cccc`, `project skills`, and `agents external`.

#### Scenario: Guided tour checks include DSH and post-3.0.0 concepts
- **WHEN** an operator runs onboarding or subsystem exploration through `houmao-admin-welcome`
- **THEN** `references/guided-paths.md` includes `dsh` alongside `claude`, `codex`, and `kimi`, plus gateway access policy, versioned files, external agents, and system-skill packs
- **AND THEN** `references/concepts.md` accurately introduces `dsh`, `service`/`web` modes, `--executor`, `houmao-mgr manual`, open-roster dashboard, usage records, and `houmao-cccc`

### Requirement: Admin welcome skill tightens reference overlap for concise guidance
`houmao-admin-welcome` SHALL remove duplicated presentation and handoff prose between `SKILL.md` and `references/orientation.md` / `references/admin-handoff.md` and tighten `references/question-style.md` and `references/guided-paths.md` using compact comparison tables per `imsight-agent-skill-handling`.

#### Scenario: Entrypoint and references stay non-redundant
- **WHEN** a reviewer inspects `houmao-admin-welcome` against `imsight-agent-skill-handling`
- **THEN** `SKILL.md` keeps concise numbered `## Workflow` steps, native-planning fallback, `## Subcommands` table, and `DO NOT ...` guardrails without duplicating reference prose

### Requirement: Admin welcome skill preserves explicit activation and read-only onboarding invariants
`houmao-admin-welcome` SHALL preserve explicit-only activation (`allow_implicit_invocation: false`), its strictly read-only boundary, the exact three blank-workspace choices, state-aware reorientation without restarting from `init`, and context-preserving handoff to `$houmao-admin-entrypoint`.

#### Scenario: Blank workspace onboarding preserves three read-only choices
- **WHEN** an operator invokes `houmao-admin-welcome` in a blank workspace
- **THEN** it presents only `Create Houmao Project`, `Subsystem Exploration`, and `Inspect` without mutating files, credentials, or agents
- **AND THEN** it recommends `$houmao-admin-entrypoint` rather than invoking execution siblings directly
