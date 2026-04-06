## Context

After a wave of refactors (named presets, gateway tmux-session targeting, Claude vendor auth lanes, Gemini headless support, system skill renaming), multiple docs pages now contain factual errors or omit recently added features. The issues range from a wrong port number to stale type names and missing option rows. All are documentation-only fixes with no code changes required.

## Goals / Non-Goals

**Goals:**
- Correct every factual error identified in the exploration pass (wrong values, stale type names, misleading phrasing).
- Fill small coverage gaps where a feature exists in code but the docs omit it (missing option, missing provider note).
- Keep edits surgical — change only what is wrong, do not restructure surrounding prose.

**Non-Goals:**
- Completing stub pages (e.g., expanding `agents-turn.md` or `agents-mail.md` from stubs to full references). That is a separate, larger effort tracked by existing `docs-cli-reference` spec requirements.
- Restructuring the docs site layout or navigation.
- Rewriting working sections that are technically accurate but could be better.

## Decisions

### D1: Fix `profile_based` → `cao_profile` in role-injection docs

The `RoleInjectionMethod` literal type in `models.py:27-31` uses `cao_profile`. The docs use the name `profile_based` in three places (description list, mermaid diagram, per-backend table). All three occurrences will be updated to `cao_profile`.

**Alternative considered**: Leave as-is and treat docs as user-facing alias. Rejected — the docs explicitly reference the `RoleInjectionMethod` type and claim to enumerate its values, so the name must match.

### D2: Fix default port 9890 → 9889 in passive-server comparison table

`houmao-server` binds to `127.0.0.1:9889` by default (`server/config.py:24`, `server/commands/serve.py:21`). The comparison table in `houmao-passive-server.md:23` says 9890. Single cell edit.

### D3: Clarify auth-option naming in houmao-mgr.md

Line 306 claims Claude credential lanes use "the same project-tool contract" in both `project agents tools claude auth add|set` and `project easy specialist create --tool claude`, then lists options with `--claude-` prefix. In reality, `project agents tools claude auth` uses unprefixed names (`--auth-token`, `--oauth-token`, `--config-dir`) while `project easy specialist create --tool claude` uses prefixed names (`--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`). The semantics are the same but the flag names differ.

Fix: reword to say "the same credential semantics" rather than "the same project-tool contract", and show both flag-name sets.

### D4: Add `--mail-account-dir` to easy-specialists.md options table

The option exists in code (`project.py:1680-1687`) and is documented in `quickstart.md` but missing from the options table in `easy-specialists.md:116-128`. Add one row.

### D5: Clarify `raw_launch` vs `local_interactive` in launch-policy.md

`launch-policy.md:22` lists `raw_launch` as an example backend surface. The `LaunchSurface` type does include `raw_launch`, but the runtime `BackendKind` type uses `local_interactive`. These are separate type aliases with overlapping but not identical value sets. Add a brief note explaining that `LaunchSurface` (build-phase) includes `raw_launch` while `BackendKind` (run-phase) uses `local_interactive`, and that `raw_launch` maps to `local_interactive` at runtime.

### D6: Clarify gateway vs internal chat-session modes in managed_agent_api.md

The doc lists 5 modes (`auto`, `new`, `current`, `tool_last_or_new`, `exact`). These are the `GatewayChatSessionSelectorMode` values accepted by the gateway API. The internal `HeadlessTurnSessionSelectionMode` only has 3 (`new`, `tool_last_or_new`, `exact`). Add a parenthetical noting that `auto` and `current` are gateway-level selectors that the gateway resolves before dispatching to the internal headless turn API.

### D7: Add Gemini exclusion note to TUI-parsing developer docs

Gemini has a headless backend but no TUI parser — this is intentional. The `tui-parsing/index.md` reading-order table and `shared-contracts.md` both describe Claude and Codex as the two providers without explaining why Gemini is absent. Add a brief note in `index.md` (after the reading-order table) and in `shared-contracts.md` (in the provider-subclasses section) stating that Gemini is headless-only by design and does not have a TUI parser.

### D8: Add system-skills introduction to README.md

The README's Usage Guide currently covers three adoption paths (join, easy specialists, full preset launch) and a subsystems-at-a-glance table, but says nothing about system skills. Users have no way to discover from the README that their agents can self-manage through packaged Houmao skills.

Add a new subsection after "Subsystems at a Glance" (before "Full Documentation") titled something like "System Skills: Agent Self-Management". Content:

- One-paragraph explanation: Houmao installs packaged skills into agent tool homes so that agents themselves can drive management tasks (specialist CRUD, credential management, definition management, instance lifecycle) without the operator manually invoking `houmao-mgr`.
- A brief table or bullet list of the four non-mailbox packaged skill families: `houmao-manage-specialist`, `houmao-manage-credentials`, `houmao-manage-agent-definition`, `houmao-manage-agent-instance`.
- Note that `agents join` and `agents launch` auto-install these by default.
- A `system-skills install --default` example for explicit external homes.
- Link to `docs/reference/cli/system-skills.md` for details.

**Placement rationale**: After the subsystems table because system skills build on top of the subsystems (gateway, mailbox) and the adoption paths (join, launch). Placing it earlier would reference concepts not yet introduced.

**Alternative considered**: Add as a row in the Subsystems table. Rejected — system skills are not a subsystem in the same sense as Gateway/Mailbox/TUI Tracking; they are a cross-cutting operator/agent interaction surface that deserves its own brief section with examples.

## Risks / Trade-offs

- **Low risk**: All changes are documentation-only. No code, API, or behavioral changes.
- **Freshness**: The chat-session mode clarification (D6) could become stale if the internal type is later expanded to match the gateway type. Acceptable — keeping docs precise now is more valuable than future-proofing a note.
