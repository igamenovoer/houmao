## Context

`houmao-touring` is the packaged system skill a first-time user is directed to by the README. It lives at `src/houmao/agents/assets/system_skills/houmao-touring/` and is shipped with the Python distribution, so every file referenced by the skill must live inside that asset directory — nothing under `examples/`, `docs/`, or `magic-context/` in the source tree is reachable after `pip install`.

The current skill already follows a clean routing model: it inspects state, explains posture, and hands off to the specialized skill that owns the requested surface. The existing spec `houmao-touring-skill` encodes that stance plus several branch-specific requirements (pairwise loop path, foreground-first gateway posture, informative question style, mailbox-root vs mailbox-account distinction, stop/relaunch/cleanup distinction).

Four gaps motivate this change:

1. The welcome message introduced recently is a single linear five-step pitch; it fights with the "orient from current state" rule when state already exists.
2. `branches/orient.md` tells the agent to offer "the next likely branches" but does not give it a lookup table, so routing varies turn-to-turn.
3. `branches/advanced-usage.md` is today strictly a pairwise-loop referral page. Other advanced skills (`houmao-memory-mgr`, `houmao-adv-usage-pattern`, `houmao-agent-gateway` extras, `houmao-agent-loop-generic`, `houmao-credential-mgr`, `houmao-agent-definition`) have no touring-level surface.
4. There is no compact glossary, so vocabulary like `specialist`, `easy profile`, `launch profile`, `recipe`, and `master` lands at the user without a self-contained reference.

There is also no ultra-short "see it run" path. The README cites `uv tool install houmao` plus skill installation, but once inside the guided tour there is no branch that says "detect what tool CLIs you already have and launch the minimum viable agent."

## Goals / Non-Goals

**Goals:**

- Make `houmao-touring` a usable entrypoint: the agent can pick the right branch deterministically from current Houmao state.
- Give first-time users a compact vocabulary reference that ships with the skill.
- Introduce a quickstart branch that adapts to the host's installed CLI tools without hard-coding one vendor as the default.
- Enumerate the broader advanced-feature surface in the advanced-usage branch as a flat list with no priority and no recommendation, so users can discover advanced skills without the tour editorializing.
- Keep the skill fully self-contained inside its packaged asset directory so the pypi-installed skill behaves the same as the in-repo skill.
- Preserve existing behavior: all current requirements in `openspec/specs/houmao-touring-skill/spec.md` remain intact; the change is additive.

**Non-Goals:**

- No new CLI commands. The skill remains a router.
- No relocation of content owned by downstream skills (project, mailbox, specialist, messaging, gateway, instance, inspect, loops, memory, email, adv-pattern, credential, agent-definition) into the tour.
- No recipe gallery, story templates, or repo-internal example references. Anything outside `src/houmao/agents/assets/system_skills/houmao-touring/` would not survive pypi packaging and is therefore out of scope.
- No change to the foreground-first gateway posture rules, the informative question-style rules, the mailbox-root-vs-account rules, or the pairwise loop routing rules.
- No change to `catalog.toml`; the skill set membership stays the same.
- No README rewrite is required as part of this change.

## Decisions

### Decision 1: State-adaptive welcome rather than always-on welcome

The welcome text is shown in full only when the workspace is blank-slate (no `.houmao/` overlay, no reusable specialists, no running managed agents). When Houmao state already exists, the skill presents a one-line acknowledgement followed by the current posture summary and the posture → branch matrix.

**Rationale:** The recently added welcome block describes a five-step initial setup. Reading it verbatim to a user who already has a project and three running agents contradicts the existing guardrail "do not force a linear step order or restart the user from project initialization when current Houmao state already exists."

**Alternative considered:** Always show the welcome. Rejected — it duplicates the orient summary and trains users to ignore the first screen of the tour.

**Alternative considered:** Remove the welcome entirely and rely only on orient output. Rejected — the welcome is the "what is Houmao" hook the README promises. Keeping it but conditionalizing it preserves both needs.

### Decision 2: Posture → branch matrix lives in `branches/orient.md`

`orient.md` gains an explicit table mapping inspected state to recommended next branches. The table is the routing source of truth for the orient branch and is referenced by SKILL.md workflow step 5 ("Explain the current posture and offer the next likely branches").

Example matrix shape (illustrative, not final content):

```
| Inspected posture                                  | Offered next branches                 |
|----------------------------------------------------|---------------------------------------|
| no overlay, no specialists, no running agents      | quickstart, setup-project-and-mailbox |
| overlay exists, no specialists                     | author-and-launch, setup-mailbox      |
| specialists exist, no running agents               | author-and-launch (launch)            |
| one or more running managed agents                 | live-operations, lifecycle-follow-up  |
| running agents plus mailbox ready                  | live-operations (mail-notifier hint)  |
| multi-agent workspace                              | advanced-usage, live-operations       |
```

**Rationale:** The current "offer the next likely branches" prose requires the agent to re-derive routing each turn. A table makes the routing deterministic and reviewable.

**Alternative considered:** A hard-coded state machine. Rejected — conflicts with the existing "do not force a linear step order" guardrail. A table of offers (not mandates) preserves the non-linear tour posture.

### Decision 3: Quickstart branch detects host-available CLI tools

`branches/quickstart.md` instructs the agent to run `command -v` for each tool adapter the packaged Houmao distribution supports (today `claude`, `codex`, `gemini`), list the tools it found, and present them to the user with no priority ordering. The user then picks one and the branch routes specialist creation + launch through `houmao-specialist-mgr` as usual.

**Rationale:** The user explicitly asked for no hard-coded vendor priority. Host detection is the cleanest way to avoid recommending a tool that is not installed while also not editorializing.

**Alternative considered:** Ask the user to type the tool name. Rejected — the tour's job is to make the obvious path obvious. If only one tool is available, presenting it without priority still effectively selects it.

**Alternative considered:** Default to claude per README. Rejected — the user explicitly refused this ordering.

**Edge case:** no supported tool is available. The branch explains which CLIs Houmao supports and routes the user to install one, then come back. It does not attempt to launch without a tool.

### Decision 4: Advanced-usage branch becomes a flat enumeration

`branches/advanced-usage.md` is expanded to list the full advanced surface as a flat brief-entry list. Each entry is one to two sentences and names the owning skill. No entry is marked as recommended, preferred, primary, or default.

Entries (expected content, not binding order):

- `houmao-agent-loop-pairwise` — stable pairwise loop plan + `start/status/stop`.
- `houmao-agent-loop-pairwise-v2` — enriched pairwise loop plan + extended run-control.
- `houmao-agent-loop-generic` — mixed pairwise + relay component graphs.
- `houmao-adv-usage-pattern` — elemental immediate driver-worker edge protocol and related composed patterns.
- `houmao-memory-mgr` — managed-agent `houmao-memo.md` and pages memory.
- `houmao-agent-gateway` — gateway mail-notifier and reminder surfaces.
- `houmao-credential-mgr` — project-local credential lifecycle.
- `houmao-agent-definition` — low-level role and preset authoring.

**Rationale:** The user asked for a brief introduction to each with no emphasis. A flat list with consistent sentence-length entries satisfies that while keeping the branch short.

**Alternative considered:** Keep the branch pairwise-only and add a new `branches/features-map.md`. Rejected — the existing spec already names this branch the "advanced-usage branch"; splitting it would force a spec rename and is unnecessary ceremony. Expanding the existing file is smaller.

**Constraint preserved:** The existing pairwise requirement and its four scenarios remain intact. The pairwise entries in the flat list carry the same routing guidance they do today; the broader list adds siblings around them without demoting them.

### Decision 5: Concepts reference ships inside the packaged asset directory

`references/concepts.md` is a single compact page. It defines vocabulary that the tour uses across multiple branches and that first-time users are most likely to stumble on. Definitions are short (one to three sentences each), concrete, and cross-reference the owning skill when relevant.

Terms covered (expected list, not binding):

- specialist, easy profile, launch profile, managed agent, recipe, tool adapter
- project overlay, `.houmao/` layout
- gateway, gateway sidecar, execution mode, foreground vs background posture
- mailbox root, mailbox account, principal id, reserved `HOUMAO-` prefix
- user agent, master, loop plan, run charter
- relaunch vs fresh launch, cleanup kinds

**Rationale:** The tour asks users to make decisions about specialists vs profiles, launch posture, and mailbox vs principal id on the first few turns. A self-contained glossary is the cheapest way to ground those decisions without duplicating downstream skill docs.

**Alternative considered:** Point at README / `docs/`. Rejected — those paths are not included in the pypi wheel. The skill must be self-contained.

### Decision 6: Self-containment guardrail is explicit in SKILL.md

A new guardrail in `SKILL.md` states that touring-skill content SHALL NOT reference paths outside `src/houmao/agents/assets/system_skills/houmao-touring/` or files that only exist in the development repository.

**Rationale:** The skill ships via pypi as part of the Houmao distribution. Any reference to `examples/`, `docs/`, `magic-context/`, or `openspec/` breaks for installed users. Making this constraint explicit prevents drift when future contributors are tempted to link out.

**Alternative considered:** Enforce via lint. Out of scope for this change; the guardrail is documentation-level here.

## Risks / Trade-offs

- [Welcome conditional drift] A future edit to `SKILL.md` might re-inline the welcome unconditionally, recreating the "restart from scratch" feeling for returning users → Mitigation: the state-adaptive rule is encoded as a spec requirement and therefore visible to spec verification; guardrail in SKILL.md also forbids forcing linear order.
- [Flat enumeration grows stale] New Houmao advanced skills land in `catalog.toml` without the `advanced-usage.md` list catching up → Mitigation: spec requires the branch to enumerate advanced skills; any proposal that introduces a new advanced skill should update this branch in the same change.
- [Quickstart host detection noise] If the host PATH contains shims that pass `command -v` but cannot actually run (e.g. broken wrapper), the branch may list an unusable tool → Mitigation: the branch only enumerates; the actual launch is routed through `houmao-specialist-mgr`, which owns failure reporting. The branch explicitly warns that a listed tool still needs valid credentials configured.
- [Concepts reference drifts from downstream skills] If downstream skills change vocabulary, the glossary can go out of sync → Mitigation: keep definitions short and cross-reference owning skills; treat downstream skill as source of truth and glossary as orientation aid.
- [Pypi packaging regression] New files under the asset directory must be included in the distribution → Mitigation: existing `branches/` and `references/` directories are already packaged; new files live alongside them with no new top-level directories.

## Migration Plan

- This is an additive packaged-asset change. There is no runtime migration.
- Deploy path: edit files in place, run `pixi run lint` and `pixi run typecheck` for safety, then ship in the next release.
- Rollback: revert the commit. Skill is self-contained; reverting the asset directory restores prior behavior.

## Open Questions

- None blocking. The user has answered: (1) enumerate advanced skills with brief intros only and no emphasis, (2) quickstart detects host tools without priority, (3) no repo-internal examples because the skill ships via pypi, (4) capture this as an OpenSpec change.
