## Context

The project `README.md` and `docs/getting-started/system-skills-overview.md` are the two highest-traffic discovery surfaces for Houmao. Both were last synced around commit `634a98fe` (post-v0.4 refresh). Since then, the `houmao-loop-planner` system skill was added to the catalog and auto-install set, two new maintained demos were shipped, and `houmao-passive-server` stabilized as a documented entrypoint. All four gaps are additive text edits — no structural, code, or navigation changes required.

## Goals / Non-Goals

**Goals:**

- Bring the README system-skills table to 15/15 skills (add `houmao-loop-planner`).
- Update the README `user-control` set enumeration to list all 7 members.
- Add the two new maintained demos to the README "Runnable Demos" section.
- Add a `Passive Server` row to the README "Subsystems at a Glance" table.
- Add `houmao-loop-planner` to the system-skills-overview getting-started guide.

**Non-Goals:**

- Reasoning preset ladder reference page (minor, deferred).
- Rewriting or restructuring any existing docs beyond the targeted insertions.
- Touching mkdocs.yml navigation (auto-generated, no action needed).

## Decisions

**D1: Add loop-planner as manual-invocation-only in docs.**
The catalog entry and SKILL.md both state `houmao-loop-planner` is manual-invocation-only. The README table row and overview guide entry will mark it accordingly, matching the precedent set by `houmao-touring`. This is consistent with the SKILL.md header which says "Use this Houmao skill only when the user explicitly asks for `houmao-loop-planner`."

**D2: List new demos with the same pattern as existing entries.**
The two new demos (`single-agent-gateway-wakeup-headless/`, `shared-tui-tracking-demo-pack/`) each have a runner script and a README. The README "Runnable Demos" section uses a name + one-paragraph description + code block pattern — the new entries will follow the same format, sourcing descriptions from `scripts/demo/README.md`.

**D3: Add passive-server to subsystems table with "Stabilizing" qualifier.**
The README CLI entry-points table already describes `houmao-passive-server` as "Stabilizing — usable for the documented surfaces". The subsystems table row will use the same status qualifier and link to the existing `docs/reference/cli/houmao-passive-server.md`.

## Risks / Trade-offs

- [Low] Demo descriptions may drift again if new demos are added without a README sync. → Mitigation: the `scripts/demo/README.md` is the canonical demo index; the project README points there for details.
- [Low] Passive-server subsystems row may need rewording when the server reaches "Stable." → Mitigation: a future release can update the qualifier.
