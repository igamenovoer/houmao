# Feature Request: Gemini Parser Architecture (Headless-Only for Now)

## Status
Proposed (Deferred from `versioned-shadow-parser-superset`)

## Summary
Gemini parser work should be handled in a dedicated change with its own design.

For now:
- keep Gemini on existing headless mode behavior,
- do not introduce Gemini TUI parsing in the current shadow-parser-superset work,
- do not force Gemini into Codex/Claude CAO TUI parser contracts.

## Why
Gemini has a different runtime shape from Codex/Claude in this repo:
- current usage is headless-mode oriented,
- upstream CAO does not currently ship a Gemini provider,
- parser contracts for structured headless output and TUI scrollback parsing are different enough that forcing one shared design now adds risk.

## Requested Future Scope
Create a dedicated Gemini parser design/change that decides:
1. Whether to keep Gemini strictly headless-only long-term, or add a TUI/CAO transport path.
2. The canonical parsing contract for headless output (event schema, completion invariants, anomaly semantics).
3. Failure semantics for drifted headless output (hard-fail vs soft-anomaly behavior).
4. Fixture/test strategy for stable and drifted Gemini outputs.

## Explicit Non-Goals (for current change)
- No Gemini TUI parser implementation.
- No Gemini parser-stack integration work under `versioned-shadow-parser-superset`.
- No behavior changes to existing Gemini headless runtime path.

## Suggested Follow-Up Deliverables
- New OpenSpec change focused on Gemini parser architecture.
- Design doc comparing headless-only vs dual-transport (headless + TUI) approaches.
- Clear acceptance criteria and migration plan independent from Codex/Claude CAO shadow parsing.

