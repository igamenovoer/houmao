# Issue 006: Version Preset Treadmill — Every CLI Release Is a Potential Regression

> Obsolete as of 2026-04-08.
> Moved from `context/issues/known/` to `context/issues/obsolete/`.
> Retained for historical reference only.


## Priority
P3 — Maintenance burden; silent regressions on upstream tool updates.

## Status
Known.

## Review Reference
Code review sections: 2.4, 4.6

## Summary

The shadow parser maintains hard-coded presets per known CLI tool version. Each new Claude Code or Codex release can change:

- Prompt characters (`>` → `❯`)
- Response markers (`⏺` → `●`)
- Spinner format (parenthesized suffix requirement changes)
- Menu/approval wording
- Banner format

Unknown versions fall back to the latest known preset with an `unknown_version_floor_used` anomaly logged. The parser can't know it's wrong until a real failure occurs in production.

## Root Cause

The system is structurally coupled to implementation details of third-party CLI tools' visual output, with no negotiated contract between the tools and the parser.

## Affected Code

- `src/houmao/agents/realm_controller/backends/claude_code_shadow.py` — `_PRESETS` dict, `_compiled_for_preset()`, `_resolve_preset()`
- `src/houmao/agents/realm_controller/backends/codex_shadow.py` — `_PRESETS` dict, equivalent methods

## Fix Direction

### Structured version negotiation (4.6)

1. At `start-session`, query the tool for its version (e.g., `claude --version` or read the banner).
2. Store the version in `CaoSessionState`.
3. Select the preset once at session start, not on every snapshot.
4. If unknown version, log a warning and proceed with latest-known — but do this once, not per poll.

Longer-term: work with tool authors to emit machine-readable status signals (structured status line at a known position) rather than relying on visual parsing of decorative TUI output.

## Connections

- The capability probe in issue-004 could incorporate version detection as part of preflight
- Lower priority because the current fallback-to-latest behavior works in practice for minor version bumps; the risk is major TUI redesigns
