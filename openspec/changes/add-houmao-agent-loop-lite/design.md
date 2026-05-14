## Context

Houmao currently has `houmao-agent-loop-pro` as the maintained loop authoring and generated-loop execution skill. Pro intentionally supports a rich generated execplan package: process-first specs, TOML contracts, JSON schemas, generated harness commands, generated skills, agent bindings, final docs, topology validation, and controlled lifecycle operation.

The lite skill is for a different use case: small or medium loops where the operator wants the same broad pro directory spine but wants the loop contract to stay readable and directly editable as Markdown plus SQL. The user direction is explicit: no JSON schema, no Jinja2, no harness, no docs layer, no separate objective/organization/contract machinery outside Markdown, direct SQLite manipulation by agents, required communication templates, and required generated skills.

One current OpenSpec change, `retire-legacy-loop-skills`, says pro is the only maintained loop skill after retiring pairwise and generic packages. This change does not revive retired package names. It adds one new maintained peer: `houmao-agent-loop-lite`.

## Goals / Non-Goals

**Goals:**

- Add a current packaged system skill named `houmao-agent-loop-lite`.
- Keep the familiar pro loop root spine: `intention/`, `execplan/`, and `runs/`.
- Keep the familiar pro execplan concern areas only where they are needed: `specs/`, `skills/`, and `agents/`.
- Make lite defaults as small as possible. Optional files and directories do not appear unless the generated loop actually needs them.
- Require plain Markdown communication templates with a loop-local type prologue for receiver dispatch.
- Require generated skills and make them the operational API that replaces pro harness/schema machinery.
- Use direct SQLite through `state/schema.sql` and `state/README.md` for loop-local runtime bookkeeping.
- Preserve Houmao mail envelope ownership. Lite templates do not duplicate sender, recipient, subject, message id, thread id, timestamps, reply refs, or system headers in the body.
- Route platform mechanics through maintained Houmao skills instead of embedding mailbox, gateway, workspace, launch, or inspection procedures in lite.

**Non-Goals:**

- Do not remove or weaken `houmao-agent-loop-pro`.
- Do not add JSON schemas, TOML contract registries, Jinja renderers, or generated harness scripts to lite.
- Do not generate `execplan/harness/` or `execplan/docs/` for lite.
- Do not auto-migrate existing pro execplans or retired pairwise/generic loop packages into lite.
- Do not make lite the default route for generic loop requests. Lite is manual-invocation-only.
- Do not expose new Houmao mailbox API fields solely to carry lite template type metadata.

## Decisions

### 1. Lite is a maintained peer to pro

`houmao-agent-loop-lite` should be cataloged beside `houmao-agent-loop-pro`, not underneath it and not as a retired-package compatibility wrapper. Pro remains the heavyweight generated-execplan path. Lite owns Markdown/direct-SQL generated loop packages.

Alternative considered: make lite a mode inside pro. Rejected because pro's existing routing and subskill set assume generated contracts, harnesses, and staged execplan depth. A separate skill keeps activation, validation expectations, and docs clear.

### 2. Preserve the pro spine, remove unused layers

Lite keeps:

```text
<loop-dir>/
  intention/
  execplan/
    specs/
    skills/
    agents/
  runs/
```

Lite does not generate:

```text
execplan/harness/
execplan/docs/
```

The default complete lite package should be close to:

```text
<loop-dir>/
  intention/
    README.md
    loop-overview.md
  execplan/
    README.md
    manifest.md
    specs/
      README.md
      objective.md
      organization.md
      process.md
      communication.md
      templates/
        task-request.md
        task-result.md
      state/
        README.md
        schema.sql
    skills/
      README.md
      <generated-skill>/SKILL.md
    agents/
      README.md
      bindings.md
  runs/
```

Optional files such as `workspace.md`, `run-artifacts.md`, `state/seed.sql`, `state/queries.md`, notifier prompts, concrete profile definitions, operator-control skills, and tick skills appear only when selected by the generated lite process.

### 3. Markdown is the lite contract format

Lite uses Markdown for the manifest, objective, organization, process, communication, agent bindings, and generated skill instructions. Markdown specs are the authority; there is no parallel machine-readable contract registry.

Alternative considered: use TOML for the manifest and bindings while keeping templates in Markdown. Rejected because the lite value proposition is a single readable contract style except for SQL state.

### 4. Templates are required and body-local

Every lite execplan has communication templates under `execplan/specs/templates/`. A template is plain Markdown with literal placeholders and a short body-local prologue:

```markdown
Loop-Template-Type: task-request
Loop-Template-Version: 1

# Task Request

Work item: <placeholder work_item_id>
```

The prologue ends at the first blank line. It is not YAML front matter and does not repeat Houmao canonical mail front matter. Generated receiver skills dispatch on `Loop-Template-Type` after reading `body_text` from Houmao mail.

Alternative considered: put type metadata into Houmao mail `headers`. Rejected for lite because ordinary `/v1/mail/send` and fallback send flows do not expose arbitrary custom headers as the agent-facing path, while the body is uniformly available.

### 5. Generated skills are required

Generated skills are not optional support material in lite. They are the operational API for agents. A lite execplan is invalid unless generated skills exist and every required `Loop-Template-Type` has at least one generated receiver skill naming that type.

The generated shared skill owns common rules: read order, placeholder replacement, no unresolved placeholders before send, direct SQLite discipline, envelope-vs-body boundary, and stop-after-one-turn behavior. Role/event/tick/operator skills are generated only when the loop process needs them.

### 6. SQLite is direct, not wrapped

Lite uses `execplan/specs/state/schema.sql` as the field-level state authority and `execplan/specs/state/README.md` as the direct-use contract for agents. Each run uses a runtime DB such as `runs/<run-id>/state.sqlite3`. Generated skills may tell agents to run `sqlite3` directly, use short transactions, and record audit rows.

The state model stores compact facts: run ids, participant ids, work item ids, ownership, status, mail refs, artifact paths, decisions, timestamps, and events. It does not store full mail bodies, long rationale, or rendered Markdown. Houmao mail and artifacts remain the rich-content authority.

Alternative considered: keep a tiny generated SQLite harness. Rejected because the user explicitly wants no harness and direct DB manipulation.

### 7. Platform mechanics remain outside lite

Lite generated skills may route work to `houmao-agent-email-comms`, `houmao-process-emails-via-gateway`, `houmao-agent-gateway`, `houmao-agent-messaging`, `houmao-agent-instance`, `houmao-agent-inspect`, `houmao-agent-definition`, and `houmao-utils-workspace-mgr` as needed. They should not duplicate those maintained skill contracts.

Lite inherits the same runtime mail rule as pro: on-event and tick behavior is prompt-triggered and bounded. Agents do not sleep, poll, tail logs, or wait in-chat for future mail.

## Risks / Trade-offs

- [Direct SQLite edits are easier to corrupt than harness-mediated records] -> Mitigate with explicit transaction recipes, short writer sections, audit tables, forbidden operations, and generated skills that point at named SQL snippets in `state/README.md` or `state/queries.md` when present.
- [Body-local template type can be damaged by freeform editing] -> Mitigate by requiring the first body paragraph prologue, generated receiver fallback for missing or unknown types, and validation that templates declare unique `Loop-Template-Type` values.
- [Two maintained loop skills reintroduce routing ambiguity after retiring legacy packages] -> Mitigate with manual-invocation-only activation and clear docs: lite for Markdown/direct-SQL/no-harness loops, pro for schemas/harness/complex generated execplans.
- [No generated docs layer makes operator onboarding thinner] -> Mitigate by keeping required `README.md` files only where they are operationally necessary, especially `execplan/README.md`, `specs/README.md`, `skills/README.md`, `agents/README.md`, and `state/README.md`.
- [Active `retire-legacy-loop-skills` says pro is the only current loop skill] -> Mitigate by treating this change as a follow-up that preserves the retired-package cleanup but revises current loop inventory to `pro` plus `lite`.

## Migration Plan

1. Add the packaged `houmao-agent-loop-lite` skill asset with minimal routing, authoring, validation, and execution guidance.
2. Add lite to the packaged current system-skill catalog and to `core` / `all` install sets beside pro.
3. Update project-scope skill projections or symlinks if those tracked surfaces expose current core skills.
4. Update docs and system-skill references to present `pro` and `lite` as the two current loop choices.
5. Add tests for catalog membership, skill installation, skill content constraints, generated default scaffold shape, template typing, generated-skill requirements, and docs inventory.

Rollback is straightforward before release: remove lite from the catalog and docs, delete the new skill asset, restore tests to pro-only current loop expectations, and leave retired loop cleanup unchanged.

## Open Questions

- Should `houmao-agent-loop-lite` include a packaged scaffold helper script, or should the skill instruct the agent to create the small Markdown tree directly? The default package is small enough that direct generation may be clearer.
- Should lite live in both `core` and `all` by default? This proposal assumes yes so managed agents can author either current loop style without reinstalling skills.
