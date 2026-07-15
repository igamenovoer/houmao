## Why

Houmao's maintained Codex and Kimi contracts lag the currently installed CLIs. Codex GPT-5.6 reasoning levels and collaboration events are misrepresented, Kimi 0.23.x is rejected by the launch-policy registry, and both current TUIs are classified with profiles derived from much older surfaces.

## What Changes

- Add model-specific Codex GPT-5.6 reasoning ladders: six positive levels for Sol and Terra through `ultra`, and five for Luna through `max`.
- Add Kimi reasoning-level projection from the selected model alias's declared effort capabilities, with explicit rejection when no trustworthy ladder is available.
- **BREAKING**: replace the maintained Kimi 0.10/0.11 launch-policy contract with a Kimi 0.23.x contract; no compatibility shim remains for the obsolete startup workaround.
- Use Kimi's native `--auto` TUI flag for fresh and resumed unattended sessions, and remove the synthetic `/auto on` bootstrap turn. Keep headless `-p` on Kimi's native automatic approval and no-question behavior without adding prompt-mode-incompatible flags.
- Normalize Codex `collab_tool_call` events and Kimi retry metadata into canonical headless action, progress, and diagnostic events.
- Refresh the Kimi adapter environment allowlist to the current upstream model and thinking variables, removing obsolete variables.
- Add bounded Codex 0.144.x and Kimi 0.23.x TUI profile selection. Preserve old profile bounds only where their recorded evidence applies, and fall back conservatively across unvalidated version gaps.
- Record, manually label, and replay current unattended Codex and Kimi TUI sessions at high capture rates and varied lower replay rates. Cover GPT-5.6 delegation and current Kimi activity, tool, retry, and ready surfaces.
- Update tests, reference documentation, getting-started guidance, and relevant packaged system-skill guidance to describe only the refreshed contracts.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-model-selection`: define current Codex GPT-5.6 reasoning ladders and capability-derived Kimi effort projection.
- `versioned-launch-policy-registry`: replace obsolete Kimi strategy coverage with maintained 0.23.x headless and unattended TUI behavior.
- `headless-output-rendering`: normalize Codex collaboration lifecycle events and Kimi retry metadata.
- `houmao-mgr-project-agent-tools`: align the starter Kimi adapter's environment contract with current Kimi Code.
- `kimi-code-tui-support`: require native `--auto` unattended startup and resume without conversational bootstrap commands.
- `codex-tui-state-tracking`: define meaningful tracked state while GPT-5.6 delegated agents are active or settling.
- `versioned-tui-signal-profiles`: bound old detector profiles and add profiles derived from Codex 0.144.x and Kimi 0.23.x recordings.
- `shared-tui-tracking-recorded-validation`: validate current Codex and Kimi profiles against high-rate labels and varied lower-rate replay streams.
- `kimi-tui-signal-corpus`: refresh the maintained Kimi corpus against 0.23.x unattended surfaces.
- `docs-launch-policy-reference`: document the refreshed Kimi launch-policy version and native unattended behavior.
- `docs-run-phase-reference`: document current Codex/Kimi headless and TUI lifecycle semantics.
- `docs-getting-started`: remove stale Kimi 0.11 guidance from onboarding documentation.
- `docs-easy-specialist-guide`: document current Codex and Kimi reasoning-level mappings.

## Impact

This change affects model mapping, runtime-home projection, launch-policy YAML and provider hooks, Kimi adapter assets, canonical headless parsing/rendering, TUI profile registration and detectors, terminal-record fixtures, unit and integration tests, documentation, and packaged system skills. Maintained Kimi support moves to 0.23.x. Codex current-version support targets CLI 0.144.x and its bundled GPT-5.6 catalog.
