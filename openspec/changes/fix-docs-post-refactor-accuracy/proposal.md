## Why

Recent refactors — named preset migration (72eec5a), gateway and agent management workflow updates (73d56b5), new system skills (6bf5c53, 22d702a, 54f1f40), Claude vendor auth lanes (5f8c3ed), launch yolo removal (59d4dd3), and Gemini headless support (742782c ff.) — introduced factual errors, stale terminology, and missing coverage across `docs/` and `README.md`. These are not structural rewrites; they are surgical corrections to values, names, and option tables that now contradict the live code, plus a new README section introducing system skills so users know agents can drive Houmao management via installed skills.

## What Changes

- Fix wrong default port for `houmao-server` in the `houmao-passive-server.md` comparison table (9890 → 9889).
- Fix `profile_based` → `cao_profile` in `run-phase/role-injection.md` to match the `RoleInjectionMethod` literal.
- Fix misleading "same options" claim in `houmao-mgr.md` for `project easy specialist create --tool claude` vs `project agents tools claude auth` (prefixed vs unprefixed option names).
- Add missing `--mail-account-dir` row to the options table in `easy-specialists.md`.
- Clarify `raw_launch` vs `local_interactive` discrepancy in `build-phase/launch-policy.md` (the `LaunchSurface` type includes `raw_launch`, the runtime `BackendKind` uses `local_interactive`; doc should explain the distinction).
- Clarify gateway-level vs internal chat-session selector modes in `managed_agent_api.md`.
- Add explicit note in `developer/tui-parsing/` docs that Gemini is intentionally unsupported for TUI tracking (headless-only by design).
- Update `README.md` to add a "System Skills" subsection in the Usage Guide introducing the system-skills surface: what it is, what it gives agents, and how to install/inspect. This lets users know that their agents can drive Houmao management (specialist CRUD, credential management, definition management, instance lifecycle) through packaged skills.

## Capabilities

### New Capabilities

- `docs-readme-system-skills`: Add a system-skills introduction to the README.md usage section so users discover that agents can self-manage through installed Houmao skills.

### Modified Capabilities

- `docs-cli-reference`: Fix wrong port, misleading auth-option phrasing, and missing option row in CLI reference pages.
- `docs-run-phase-reference`: Fix `profile_based` → `cao_profile` terminology; clarify `raw_launch` / `local_interactive` surface distinction.
- `docs-developer-guides`: Add Gemini exclusion note to TUI-parsing developer docs.
- `docs-subsystem-reference`: Clarify gateway vs internal chat-session selector modes in managed-agent API doc.

## Impact

Documentation only — no code, API, or dependency changes. Affected files:

- `README.md`
- `docs/reference/cli/houmao-passive-server.md`
- `docs/reference/cli/houmao-mgr.md`
- `docs/reference/cli/system-skills.md`
- `docs/getting-started/easy-specialists.md`
- `docs/reference/run-phase/role-injection.md`
- `docs/reference/build-phase/launch-policy.md`
- `docs/reference/managed_agent_api.md`
- `docs/developer/tui-parsing/index.md`
- `docs/developer/tui-parsing/maintenance.md`
- `docs/developer/tui-parsing/shared-contracts.md`
