## 1. Fix Factual Errors

- [x] 1.1 In `docs/reference/cli/houmao-passive-server.md`, change the comparison table default port for `houmao-server` from `9890` to `9889` (line 23).
- [x] 1.2 In `docs/reference/run-phase/role-injection.md`, replace all three occurrences of `profile_based` with `cao_profile`: the description list item (line 60), the Mermaid diagram node label (line 20), and the per-backend strategy table rows for `cao_rest` and `houmao_server_rest` (lines 71-72).
- [x] 1.3 In `docs/reference/cli/houmao-mgr.md` (line 306), reword the Claude credential lanes note to say "the same credential semantics" instead of "the same project-tool contract", and show both flag-name sets: unprefixed (`--auth-token`, `--oauth-token`, `--config-dir`) for `project agents tools claude auth` and prefixed (`--claude-auth-token`, `--claude-oauth-token`, `--claude-config-dir`) for `project easy specialist create --tool claude`.

## 2. Fill Missing Coverage

- [x] 2.1 In `docs/getting-started/easy-specialists.md`, add a `--mail-account-dir` row to the instance launch options table (after line 127) with default `None` and description "Optional private filesystem mailbox directory to symlink into the shared root."
- [x] 2.2 In `docs/developer/tui-parsing/index.md`, add a note after the reading-order table explaining that Gemini is headless-only by design and does not have a TUI parser.
- [x] 2.3 In `docs/developer/tui-parsing/shared-contracts.md`, add a note in the provider-subclasses section stating that `ClaudeSurfaceAssessment` and `CodexSurfaceAssessment` are the only two TUI-tracked providers and that Gemini is excluded by design.

## 3. Clarify Terminology Drift

- [x] 3.1 In `docs/reference/build-phase/launch-policy.md` (line 22), add a parenthetical or footnote explaining that `LaunchSurface` (build-phase) includes `raw_launch` while `BackendKind` (run-phase) uses `local_interactive`, and that `raw_launch` maps to `local_interactive` at runtime.
- [x] 3.2 In `docs/reference/managed_agent_api.md` (line 252), add a parenthetical noting that `auto` and `current` are gateway-level selectors (`GatewayChatSessionSelectorMode`) resolved by the gateway before dispatch, and that the internal headless turn API accepts only `new`, `tool_last_or_new`, and `exact`.

## 4. README Updates

- [x] 4.1 Review `README.md` command examples and descriptions for accuracy against the current CLI (flag names, defaults, command output). Fix any stale content found.
- [x] 4.2 Add a "System Skills: Agent Self-Management" subsection after the "Subsystems at a Glance" table and before "Full Documentation". Include: a one-paragraph explanation of the system-skills surface, a table of the four non-mailbox skill families with brief descriptions, a note that `agents join` and `agents launch` auto-install these by default, a `system-skills install --default` example for explicit external homes, and a link to `docs/reference/cli/system-skills.md`.
