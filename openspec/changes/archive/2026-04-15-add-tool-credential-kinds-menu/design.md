## Context

Today's credential ask-flow in `houmao-specialist-mgr/actions/create.md` and `houmao-credential-mgr/actions/add.md` tells the agent to ask the user for "missing auth inputs" but provides no enumerated, user-facing kind menu. The per-tool `*-credential-lookup.md` references in `houmao-specialist-mgr` document discovery rules (Env Lookup / Directory Scan / Auto Credentials) and importable forms, framed as "given an existing auth shape, map it to these flags" — not as "here's what kinds you can pick from".

Each tool supports multiple credential kinds:

- **Claude**: `--api-key` (`ANTHROPIC_API_KEY`), `--claude-auth-token` (`ANTHROPIC_AUTH_TOKEN`), `--claude-oauth-token` (`CLAUDE_CODE_OAUTH_TOKEN`), `--claude-config-dir` (vendor-login directory containing `.credentials.json` plus optional `.claude.json`), plus optional `--base-url`, `--claude-model`, and optional `--claude-state-template-file` as reusable bootstrap state (not a credential).
- **Codex**: `--api-key` (`OPENAI_API_KEY`), `--codex-auth-json` (`auth.json`), config-backed env-only provider with preconditions, plus optional `--base-url`, `--codex-org-id`.
- **Gemini**: `--api-key` (`GEMINI_API_KEY`), `--google-api-key` with `--use-vertex-ai` for the Vertex AI lane, `--gemini-oauth-creds` (`.gemini/oauth_creds.json`), plus optional `--base-url`.

The same set of kinds maps to the `project credentials <tool> add` flags in `houmao-credential-mgr` with slightly different flag spellings (for example `--oauth-token` in credential-mgr vs `--claude-oauth-token` in specialist-mgr, `--auth-json` vs `--codex-auth-json`, `--oauth-creds` vs `--gemini-oauth-creds`, `--config-dir` vs `--claude-config-dir`). The kinds themselves are the same across the two skills; the flag spellings differ because each skill owns a different CLI surface.

`houmao-specialist-mgr` and `houmao-credential-mgr` ship as independently installed skill asset directories. After `pip install houmao`, each skill can be installed on its own; cross-skill file references cannot resolve. This forces a choice between duplication and centralization.

## Goals / Non-Goals

**Goals:**

- Give the agent a per-tool, user-facing credential kinds menu to cite when asking the user for missing auth.
- Place the menu next to each skill's own action pages so every skill that asks about credentials can reach it without cross-skill links.
- Keep kinds pages authored in plain user-facing language (not flag-table style), so first-time users can read them.
- Keep the existing one-shot CLI pattern intact: `project easy specialist create --<auth-flag> ...` remains the recommended shape for specialist-mgr; nothing in the workflow forces an agent to split credential creation into a separate `project credentials <tool> add` first.
- Keep existing lookup references (`*-credential-lookup.md` in specialist-mgr) intact and scoped to discovery only; the new kinds pages reference them rather than duplicating their discovery rules.
- Keep the change additive at the spec level — new requirements, no modifications to existing requirements.

**Non-Goals:**

- No architectural consolidation between `houmao-specialist-mgr` and `houmao-credential-mgr`. The earlier exploration discussed routing credential creation from specialist-mgr through credential-mgr; the user explicitly chose to keep the current separation (Option B from discussion).
- No move of lookup references out of `houmao-specialist-mgr` into `houmao-credential-mgr`.
- No change to `houmao-touring`. The existing routing in `branches/quickstart.md:46` already delegates credential decisions to the owning skill, and the owning skill now has a proper menu.
- No change to discovery-mode workflows (Env Lookup, Directory Scan, Auto Credentials) in `houmao-specialist-mgr/actions/create.md`. Those stay as they are.
- No change to CLI behavior or Python source.
- No recipe gallery or example auth values that would reference paths outside the packaged skill directories.

## Decisions

### Decision 1: Option B (duplicated per-skill kinds pages) rather than centralized routing

Each skill gets its own per-tool kinds pages under its own `references/` directory. Total of six new files (three per skill).

**Rationale:** Skills install as independent asset directories. Cross-skill file links do not resolve after `pip install`, so a single source of truth in one skill cannot be cited from the other. The user explicitly chose this option after the exploration weighed the alternative (routing credential creation from specialist-mgr into credential-mgr).

**Alternative considered:** Centralize the menu in `houmao-credential-mgr` and route specialist-mgr's credential-creation decisions through it. Rejected by the user because it would force the agent's specialist-creation workflow to take two command steps instead of the current one-shot, introduce a dangling-credential risk on specialist-create failure, and reorganize responsibility across two skills for a change that only needed to present a menu.

**Alternative considered:** Put the menu inline in each skill's action file. Rejected because the action files become noisy and the kinds page is reusable (any future action in the same skill that needs to ask about credentials can cite the same reference).

### Decision 2: Kinds pages are user-facing, not flag-tables

Each kinds page is organized around kinds the **user** picks from, in plain language:

```
## Kinds

### 1. <Kind name> (for example "API Key")
- Looks like: <what the user types, shape hint>
- Maps to: <--flag> in this skill's CLI surface
- Choose this when: <situation the user would describe>
- Security: <opaque vs recoverable, if relevant>

### 2. <Next kind>
...

## Discovery Shortcuts (alternative to picking a kind)

- Auto credentials — "search my host for existing auth"
- Env lookup — "check these env vars: ..."
- Directory scan — "scan this directory: ..."

(Discovery shortcut details live on `*-credential-lookup.md`; see that
 reference when a shortcut is selected.)

## Not Importable Yet

<kinds the CLI does not currently support>
```

**Rationale:** The purpose is to help the agent present a menu to a user who may not know what kinds exist. Flag tables (which we already have in action pages) do not serve that purpose.

**Alternative considered:** Just a compact flag table keyed by kind name. Rejected — it duplicates what's already in action pages and does not solve the user-facing presentation problem.

### Decision 3: Kinds pages cite existing lookup references rather than restate discovery rules

The kinds pages mention discovery modes (Auto / Env / Dir) in a compact "Discovery Shortcuts" section but do not restate the discovery rules. For actual discovery, the agent still loads the existing `*-credential-lookup.md` file as before.

**Rationale:** The lookup references already carry the discovery rules for specialist-mgr. Duplicating them into kinds pages is churn. The compact reference pointer keeps the menu one-page-readable.

**Alternative considered:** Fold discovery rules into the kinds page and retire the lookup reference. Rejected — discovery is a separate concern, and the lookup references are referenced by existing spec requirements (`houmao-create-specialist-credential-sources`). Retiring them is a bigger change out of scope.

**Credential-mgr caveat:** `houmao-credential-mgr/actions/add.md` currently requires explicit inputs; it does not have discovery modes. Its kinds pages describe discovery shortcuts informationally but flag that discovery-mode credential creation is not supported by the `project credentials <tool> add` path today — the user can either provide an explicit kind to this skill, or use `project easy specialist create` through `houmao-specialist-mgr` if they want discovery shortcuts during specialist creation.

### Decision 4: Cite kinds reference from action pages, load on demand

- `houmao-specialist-mgr/actions/create.md` step 9 (ask-for-missing-auth) gains a new line: "if the agent is asking the user to pick an explicit auth kind for the selected tool, load `references/<tool>-credential-kinds.md` and present the kinds menu from that page."
- `houmao-credential-mgr/actions/add.md` step 3 (ask-the-user) gains the analogous line for credential-mgr's kinds references.

**Rationale:** Matches the existing "load on demand" pattern already used by `*-credential-lookup.md`. The skill does not preload the kinds page; it reads it only when the agent is about to ask the user.

### Decision 5: Keep the same kinds taxonomy in both skills

The user-facing kinds are the same in both skills (API key / OAuth token / auth token / vendor-login dir or file / Vertex AI lane / etc.). Each skill's kinds page maps them to that skill's own CLI flag spellings.

**Rationale:** The user is picking the same real-world credential in either case. Differences between the two skills are flag spellings, not kind taxonomy.

**Drift risk:** If Houmao later adds a new credential kind (for example a new Claude auth shape) both skills' kinds pages must be updated in the same change. Mitigated by the proposal requiring both sides to be updated together when either is touched.

## Risks / Trade-offs

- [Duplication drift] Six kinds pages across two skills covering three tools means future credential-shape additions must touch both skills → Mitigation: the new spec requirements explicitly name the six files so future changes cannot legitimately update one side only without a targeted spec decision. The existing lookup references and action pages already have a similar "keep in sync" expectation, and this change follows the same pattern.
- [User confusion between kinds page and lookup page] A reader might read the kinds page and expect discovery rules, or read the lookup page and expect a menu → Mitigation: each page opens with a "Use this reference when ..." line that names its narrow purpose; kinds cite lookup for discovery and lookup continues to describe itself as discovery-only.
- [Kinds page becomes a flag table anyway] Authors might drift toward "just list the flags" framing → Mitigation: kinds pages carry a fixed kind-first structure and the spec requires user-facing language.
- [Test suite substring assertions] `tests/unit/agents/test_system_skills.py` currently asserts specific substrings in `create.md` and related files. Changing the step-9 text or adding new reference files may need test updates → Mitigation: the implementation plan runs the full test suite and updates the test assertions at implementation time.
- [Kinds page bloat] Claude has four kinds plus two optional modifiers plus optional state template — the kinds page for Claude could grow long → Mitigation: keep each kind's entry to roughly one-half to one full screen; push discovery detail to the lookup reference.
- [Credential-mgr discovery gap] `actions/add.md` has no discovery modes today; adding discovery shortcuts to the kinds page creates an expectation it may not fulfill → Mitigation: kinds page explicitly states that credential-mgr does not currently run discovery modes in `add`, and points the user to specialist-mgr's create action if they want discovery-mode credential import.

## Migration Plan

- Additive packaged-asset change. No runtime migration.
- Deploy path: edit files in place, run `pixi run lint`, run `pixi run test`, ship in the next release.
- Rollback: revert the commit. The two skills remain self-contained.

## Open Questions

- None blocking. The user's earlier answers settled: (1) accept Option B duplication, (2) keep `houmao-specialist-mgr` one-shot creation, (3) no architectural consolidation or routing from specialist-mgr to credential-mgr, (4) formalize as an OpenSpec change.
