## Context

Two code features shipped without corresponding README updates: agent workspace unification (`agents workspace` command family, `memory/` under the overlay) and mail-notifier notification mode (`any_inbox` vs `unread_only`). Separately, `docs/index.md` is a bare link list that gives installed users no orientation, `DEVLEPMENT-SETUP.md` has a typo in its filename, and `docs/getting-started/quickstart.md` silently assumes a from-source checkout (uses `pixi run` throughout) without telling installed users how to adapt.

The change is entirely documentation. No source code changes. No API surface changes.

## Goals / Non-Goals

**Goals:**
- Bring README content current with workspace unification and mail-notifier notification mode features
- Give `docs/index.md` a brief intro and audience-oriented "where to start" table without removing any existing link
- Fix the `DEVLEPMENT-SETUP.md` filename typo
- Annotate `docs/getting-started/quickstart.md` so installed users know they can drop `pixi run`

**Non-Goals:**
- Changing README section order or Quick Start step count/numbering
- Removing or reorganizing content within `docs/index.md`
- Expanding `DEVLEPMENT-SETUP.md` into a full contributor guide
- Splitting `quickstart.md` into separate pages per audience

## Decisions

### Decision: README receives surgical additions only

The `readme-structure` spec and the user have both confirmed the current 7-step structure (steps 0–6, with step 1 = "Drive with Your CLI Agent") must not change. Changes are limited to:
- Adding `memory/` to the overlay layout bullet list in step 2 (Initialize a Project)
- Adding one or two `agents workspace` rows to the join capabilities table in step 5 (Adopt an Existing Session)
- Adding a pointer to the Managed Agent Workspaces guide in step 3 (Create Specialists & Launch Agents) or the See Also material at the bottom of step 2

Mail-notifier notification mode (`any_inbox` / `unread_only`) is a detail-level change. The README already describes the gateway skill as "manage gateway mail-notifier behavior," which remains accurate. No README change needed for this feature.

### Decision: `docs/index.md` gets an intro block prepended, not restructured

The existing link sections are correct and complete. Rather than restructuring them, a short block is added at the very top:
- 2–3 sentences: what Houmao is, who this site is for (installed users + some developer info)
- A small "where to start" table with three rows: installed user, from-source developer, contributor

This is purely additive — no existing links are removed or reordered.

### Decision: `DEVLEPMENT-SETUP.md` is renamed, no content change

The file content is accurate for contributors using Codex. Only the filename is corrected. Any file in the repo that hard-links this filename must be updated at the same time.

### Decision: `quickstart.md` gets a top-of-page note, not restructured

The guide's content is correct for from-source developers. A short callout at the top tells installed users that every `pixi run houmao-mgr ...` becomes simply `houmao-mgr ...` for them. This is the least disruptive fix: no steps are moved or split, and both audiences get what they need from one page.

### Decision: `readme-structure` spec updated to match current 7-step README

The existing spec describes a 6-step README (steps 0–5) that was superseded when "Drive with Your CLI Agent" was inserted as step 1. The delta spec corrects the section-ordering requirement to reflect steps 0–6, adds a requirement for the new step 1 content, and adds a requirement that workspace content (memory/ overlay entry, agents workspace pointer) appears in step 2 / step 5.

## Risks / Trade-offs

- **Risk**: Some external link or navigation tree outside the repo still points to `DEVLEPMENT-SETUP.md`. → Mitigation: grep the full repo for all references before renaming; update any found.
- **Risk**: The quickstart "installed user" annotation may fall out of date if the commands change. → Mitigation: the note is written in terms of a general rule (drop `pixi run`) rather than listing specific commands, so it stays accurate as long as `houmao-mgr` is the installed entrypoint.
