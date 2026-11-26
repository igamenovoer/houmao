# Spec Delta

## ADDED Requirements

### Requirement: Admin entrypoint routes post-3.0.0 operator surfaces cleanly
`houmao-admin-entrypoint` SHALL update its `When to Route Here` descriptions and operator discovery notes to cover `houmao-mgr manual`, `admin executors|cleanup`, `system-skills`, `project skills`, `project migrate`, `agents external`, `open-browser`, `houmao-cccc`, and Stalwart intranet online mail.

#### Scenario: Operator asks about post-3.0.0 admin surfaces
- **WHEN** an operator invokes `houmao-admin-entrypoint` for `project skills`, `agents external`, `open-browser`, `houmao-cccc`, or Stalwart online attachment
- **THEN** the `## Subcommands` table routes accurately to the owning `houmao-shared-routines` child without inventing new sibling skills
- **AND THEN** requests for `houmao-mgr manual`, `admin executors|cleanup`, or `system-skills` receive accurate operator guidance or routing

### Requirement: Admin entrypoint eliminates duplicate gate prose
`houmao-admin-entrypoint` SHALL tighten redundant `## Actor Contract`, `## Target Gate`, and compatibility-alias paragraphs in `SKILL.md` into concise non-duplicative clauses per `imsight-agent-skill-handling`.

#### Scenario: Entrypoint remains a lean collection router
- **WHEN** a reviewer checks `houmao-admin-entrypoint/SKILL.md`
- **THEN** `## Workflow` states intent classification, admin frame construction, and target gate once without repeating full contract paragraphs verbatim

### Requirement: Admin entrypoint preserves actor frame, target gate, and adoption invariants
`houmao-admin-entrypoint` SHALL preserve `narrow-implicit` activation, intent-first classification, immutable admin frame (`actor_kind=admin`, `verified_self_identity=null`), explicit target gate, `specialist-mgr` alias, `Joined-Session Adoption`, non-collapsing `pro`/`lite`, and `process-emails-via-gateway` rejection.

#### Scenario: Joined session adopts managed agent entrypoint
- **WHEN** `agent-instance join` succeeds under `houmao-admin-entrypoint`
- **THEN** the router keeps the admin frame until `agents self join` succeeds, runs `houmao-mgr --print-json agents self identity`, and hands off to `$houmao-agent-entrypoint`
- **AND THEN** it continues rejecting agent-only `process-emails-via-gateway` in admin posture
