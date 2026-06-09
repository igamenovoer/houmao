## Context

Houmao currently treats `operator_prompt_mode = unattended` as a maintained no-prompt contract, but Kimi only declares that contract for the `kimi_headless` backend. Kimi TUI launches use the shared `local_interactive` backend, which maps to launch-policy backend `raw_launch`; the Kimi registry has no compatible unattended strategy for that backend, so Kimi TUI agents either run `as_is` or fail compatibility if unattended is requested.

The local Kimi Code source under `extern/orphan/kimi-code` shows three relevant permission surfaces. `--auto` starts the TUI in auto permission mode. `default_permission_mode = "auto"` in `config.toml` is applied to fresh sessions when the SDK creates the main agent. The `/auto on` command calls `session.setPermission("auto")` inside an active TUI session. Kimi also rejects `--auto`, `--yolo`, and `--plan` when TUI startup uses `--continue` or `--session`, so a durable Houmao design cannot simply add `--auto` to every Kimi TUI launch command.

Kimi `auto` is the closest provider-native match for Houmao unattended: Kimi's permission policy auto-approves normal tool calls and denies `AskUserQuestion`, instructing the agent to decide and continue. It does not bypass explicit hard-deny surfaces such as PreToolUse hook blocks, user configured deny rules, or plan-mode guards. Houmao should describe that boundary as "fully automatic without asking the user" rather than "bypass every possible provider safety block."

## Goals / Non-Goals

**Goals:**

- Make `operator_prompt_mode = unattended` compatible with Kimi `local_interactive` / `raw_launch`.
- Ensure Kimi unattended TUI startup reaches Kimi `auto` permission mode before Houmao submits role bootstrap or workload prompts.
- Ensure Kimi unattended TUI relaunch and resumed-provider-session startup do not regress to manual approval prompts.
- Preserve Kimi headless prompt-mode unattended behavior.
- Preserve explicit `as_is` Kimi TUI behavior without automatic permission overrides.
- Avoid reintroducing `--yolo` as a supported Houmao launch control.

**Non-Goals:**

- Do not modify Kimi Code source.
- Do not bypass Kimi's hard-deny policy surfaces or user-authored deny rules.
- Do not add managed `--skills-dir` projection to Kimi TUI.
- Do not change Gemini, Claude, or Codex unattended semantics.
- Do not require users to supply raw Kimi `--auto` flags through launch overrides.

## Decisions

### Add a Kimi raw-launch unattended strategy

The launch-policy registry should add a Kimi strategy for `operator_prompt_mode = unattended` and backend `raw_launch`, version-scoped to the maintained Kimi TUI family. That strategy should declare Kimi `default_permission_mode` as strategy-owned runtime-home state and set it to `auto` before provider start.

Alternative considered: extend the existing `kimi_headless` strategy to list both `kimi_headless` and `raw_launch`. A separate raw-launch strategy is clearer because headless prompt mode and TUI startup have different provider contracts. Headless owns prompt placement and stream JSON, while TUI owns session startup mode and visible control.

Alternative considered: add `--auto` as a strategy-owned CLI arg. That works only for fresh TUI startup. Kimi rejects `--auto` with `--continue` or `--session`, so this would either break relaunch or require stripping the flag later.

### Use config plus runtime refresh rather than persistent raw `--auto`

For fresh Kimi TUI sessions, `default_permission_mode = "auto"` should make the provider-created main agent start in auto mode. For resumed or older sessions that may already have persisted `manual`, the local-interactive runtime should refresh permission mode by submitting Kimi's `/auto on` slash command after the TUI is ready and before any Houmao role bootstrap or workload prompt is submitted.

This two-part approach covers both fresh and resumed cases without adding forbidden resume-time CLI flags. It also keeps Kimi `as_is` behavior unchanged because the refresh runs only when the launch plan metadata records `operator_prompt_mode = unattended`.

Alternative considered: rely only on `default_permission_mode = "auto"`. That is insufficient for existing sessions because Kimi resumes the persisted session permission rather than applying fresh-session defaults.

Alternative considered: rely only on `/auto on`. That likely works, but setting the config default gives Kimi the correct permission mode from session creation and reduces the window where the TUI is manual before Houmao can submit a slash command.

### Keep resume selectors owned by relaunch, not launch overrides

Kimi raw-launch unattended canonicalization should continue removing caller-supplied low-level permission/session flags that conflict with the maintained startup contract. Provider-native resume selectors should remain owned by Houmao relaunch policy, which appends `--continue` or `--session <id>` after the stored launch plan is built.

The local-interactive Kimi relaunch guard should continue rejecting final commands that combine Kimi resume selectors with `--auto`, `--yolo`, or `--plan`. The new unattended behavior should not depend on those flags being present.

### Publish explicit launch metadata for diagnostics

Launch plans and manifests should make the selected Kimi unattended posture inspectable. Metadata should show the selected raw-launch strategy, strategy-owned `default_permission_mode = auto`, and whether a TUI auto-mode startup refresh is expected. This gives operators a concrete explanation when a Kimi TUI should not be asking for approvals.

## Risks / Trade-offs

- Kimi `/auto on` syntax could drift → Keep the maintained version range bounded and test against the local source-backed Kimi version family.
- `/auto on` submission could race with startup modals → Run it through the same readiness path used for bootstrap prompt submission and fail clearly if the TUI is not ready for managed input.
- Existing manual sessions may remain manual if refresh fails silently → Treat refresh failure as launch or relaunch failure for unattended Kimi TUI, not as a warning.
- Auto mode still honors hard-deny policy blocks → Document the boundary and avoid claiming that Houmao bypasses explicit provider deny policies.
- Config writes may overwrite unrelated Kimi TOML formatting → Use existing TOML mutation helpers and preserve unrelated keys.

## Migration Plan

No stored-data migration is required. New unattended Kimi TUI launches should set the runtime-home default permission mode during provider start. Existing preserved Kimi runtime homes are repaired on next unattended provider start. Existing Kimi sessions that relaunch in unattended mode receive the `/auto on` refresh before managed prompts are submitted.

Rollback is straightforward: remove the Kimi raw-launch unattended strategy and disable the local-interactive Kimi auto refresh. Kimi headless unattended behavior remains separate and can be left intact.

## Open Questions

- Should the Kimi TUI auto refresh be recorded as a dedicated manifest event for later audit, or is launch-plan metadata sufficient?
- Should Houmao expose a low-level diagnostic command that checks a live Kimi TUI footer/status panel for `auto` after startup?
