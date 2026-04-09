## Context

The documentation surface (README, `docs/index.md`, `docs/getting-started/system-skills-overview.md`, `docs/reference/cli/houmao-mgr.md`, and `docs/reference/managed_agent_api.md`) has drifted from the shipped runtime on three independently-landed axes:

1. **System-skill catalog size.** `src/houmao/agents/assets/system_skills/catalog.toml` ships fourteen skills; the README and the overview guide still say "twelve" and omit `houmao-agent-loop-pairwise` and `houmao-agent-loop-relay`. The ASCII install-defaults diagram in the overview guide also encodes frozen counts ("11 skills" / "12 skills") that no longer match the resolved `user-control` set.
2. **Top-level `houmao-mgr credentials` command family.** The `2026-04-09-separate-credential-management-interface` change shipped a first-class `houmao-mgr credentials claude|codex|gemini` command group (separate from `project credentials ...`), but `docs/reference/cli/houmao-mgr.md` has no `### credentials` section under "Command Groups", the README "CLI Entry Points" table makes no mention of it, and `docs/index.md` does not link to a credentials reference. The packaged `houmao-credential-mgr` skill already routes agents to `houmao-mgr credentials <tool> ... --agent-def-dir <path>`, creating an asymmetry where agent-facing docs are correct but operator-facing docs are not.
3. **Request-scoped headless execution overrides.** The `headless-execution-overrides` change added `--model` and `--reasoning-level` to `houmao-mgr agents prompt`, `houmao-mgr agents turn submit`, and `houmao-mgr agents gateway prompt`, plus equivalent payload fields on the managed-agent HTTP routes and direct gateway routes. `agents turn submit` and `agents gateway prompt` are already documented; the `agents prompt` row in `docs/reference/cli/houmao-mgr.md` is a single-line entry and does not surface the new flags, the TUI-target rejection semantics, or the no-persistence contract.

All three drifts share the same root cause: multiple recent feature changes landed while the top-level docs were owned by a different review slice. None of the three requires code or CLI changes — the runtime, the catalog, and the operator CLI are already aligned.

## Goals / Non-Goals

**Goals:**

- Make the README system-skills catalog row count match `catalog.toml` and include rows for `houmao-agent-loop-pairwise` and `houmao-agent-loop-relay`.
- Make the `docs/getting-started/system-skills-overview.md` per-skill table, narrative count, and auto-install ASCII diagram track `catalog.toml` including `[auto_install]` set expansions.
- Add a dedicated `credentials` command-group section to `docs/reference/cli/houmao-mgr.md`, surface it from the README "CLI Entry Points" table, and link it from `docs/index.md`.
- Document request-scoped headless execution overrides on all three prompt surfaces (`agents prompt`, `agents turn submit`, `agents gateway prompt`) inside `docs/reference/cli/houmao-mgr.md`, including TUI-target rejection semantics and the no-persistence contract.
- Sanity-check `docs/reference/managed_agent_api.md` so the HTTP payload coverage matches the CLI flag coverage for the same headless-override surface.

**Non-Goals:**

- No new standalone `docs/reference/cli/credentials.md` reference page. The credentials section lives inside `houmao-mgr.md` next to `brains`, `system-skills`, and `mailbox`, matching the current houmao-mgr reference shape.
- No new narrative subsection or dedicated reference page for the loop skills. Loop-skill coverage stays at catalog-row depth in this change; a deeper narrative may be proposed separately.
- No changes to `catalog.toml`, the packaged skill assets, the `srv_ctrl` command registrations, the CLI flag surface, or the managed-agent HTTP route set.
- No code-level or CLI-level refactors. This change is doc-only. Tests that assert documentation shape (for example, skill catalog test coverage) are only touched if the `catalog.toml` count is referenced in a test fixture.

## Decisions

### Decision 1: Keep `credentials` docs inside `houmao-mgr.md`

**Choice.** Document the top-level `credentials` command family as a new `### credentials — Dedicated credential management` section within `docs/reference/cli/houmao-mgr.md` rather than creating a new `docs/reference/cli/credentials.md` page.

**Rationale.** The existing reference page treats `admin`, `agents`, `mailbox`, `brains`, `system-skills`, `project`, and `server` as first-class sections inside one file. Dedicated pages are reserved for deeply-nested command families (`agents gateway`, `agents turn`, `agents mail`, `agents mailbox`, `admin cleanup`). The `credentials` family has exactly three tool subcommands and six CRUD verbs per tool — small enough to keep inline. Adding a new page would force cross-file consistency work without reducing review surface.

**Alternatives considered.**
- **New dedicated page.** Rejected: extra file to keep in sync with `project credentials` and no proportional reader benefit at current surface depth. Revisit if the credentials surface grows (for example new vendor lanes or shared operations across tools).

### Decision 2: Loop skills stay at catalog-row depth

**Choice.** Add two rows each to the README skill table and the overview-guide skill table. Do not introduce a new narrative subsection, diagram, or reference page for the loop skills in this change.

**Rationale.** The loop-skill assets already ship rich operating, authoring, references, and templates subtrees inside `src/houmao/agents/assets/system_skills/houmao-agent-loop-*/`. Agents in managed homes can already discover them. The immediate drift is that the README and the overview narrative claim the catalog has "twelve" skills, which is false. Fixing the count and listing the skills removes the user-facing lie; deciding the long-term narrative home is a separate, non-blocking design question.

**Alternatives considered.**
- **Rows plus a "Loop Skills" subsection in the overview guide.** Rejected for this change to keep the scope tight and avoid predicating the count fix on a framing decision. A follow-up change may add the narrative later.
- **Rows plus a dedicated reference page.** Rejected for the same reason, with extra cost.

### Decision 3: Strengthen requirements rather than rewrite them

**Choice.** The spec deltas use `## ADDED Requirements` where possible and reserve `## MODIFIED Requirements` for places where an existing requirement needs to carry the fourteen-skill enumeration directly. New requirements name the specific files they govern (`README.md`, `docs/getting-started/system-skills-overview.md`, `docs/reference/cli/houmao-mgr.md`) so drift becomes verifiable at review time.

**Rationale.** The docs specs already describe "the README must document system skills" and "the CLI reference must document all active command groups including `credentials`". The drift is not that the specs are wrong; it is that the implementation files do not satisfy the existing specs. Adding named-file requirements makes the next drift observable without having to re-derive the intent from narrative prose.

### Decision 4: Scope the headless-override docs to the CLI reference plus a managed-agent-API cross-check

**Choice.** The spec delta for `docs-cli-reference` adds an explicit requirement that the three prompt surfaces (`agents prompt`, `agents turn submit`, `agents gateway prompt`) must document `--model` and `--reasoning-level`, TUI-target rejection, and the no-persistence contract. The change also verifies `docs/reference/managed_agent_api.md` carries the equivalent HTTP payload coverage, but does not create a new managed-agent-API spec delta — the managed-agent-API reference requirements already live under a different capability and were exercised by the `headless-execution-overrides` change itself.

**Rationale.** Touching one more spec (for `docs-managed-agent-api` or similar) would widen review surface for a single cross-reference check. If the cross-check reveals that `managed_agent_api.md` is also stale, the correct follow-up is to raise that as a separate, bounded proposal rather than bundle it here.

## Risks / Trade-offs

- **[Risk]** Catalog count drifts again the next time a skill is added. → **Mitigation:** spec deltas encode the fourteen-skill catalog as the current authoritative count and reference `catalog.toml` by path. Future skill additions must update both the README table and the overview guide as part of the change introducing the skill. A lightweight follow-up option (not in this change) would add a test that enforces README row count against `catalog.toml` entry count, similar to how the system-skills unit tests already exercise the catalog.
- **[Risk]** The `credentials` section inside `houmao-mgr.md` diverges from future additions to the credentials command family. → **Mitigation:** the new section derives subcommand coverage from the live Click help output (consistent with the existing houmao-mgr reference convention) and keeps per-tool option tables narrow, so adding a new tool lane or CRUD verb becomes a single-section edit.
- **[Trade-off]** Keeping loop-skill coverage at catalog-row depth leaves the loop-skills narrative gap unresolved. Users who discover the skills through managed-home auto-install still have to read the `SKILL.md` inside the asset tree. Accepted because closing that gap is a larger framing decision and blocking the count fix on it would keep the README/guide misleading for longer.
- **[Trade-off]** Not creating a standalone `credentials.md` reference page means the `houmao-mgr.md` file gets longer. Accepted because the file already houses similarly-sized command-group sections and the readability hit is small compared to the cross-file consistency cost of adding a new page.
