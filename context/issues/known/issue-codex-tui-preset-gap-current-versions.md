# Issue: Codex TUI Parser Has No Preset for the Supported Version Range

Date: 2026-10-20. Found by the `add-codex-hook-observation` live qualification (task 6.2), `tmp/codex-hook-smoke/QUALIFICATION.md` finding 1.

## Symptom

At codex-cli 0.163.0 and 0.162.1 (the supported floor is `>=0.162.1` per `src/houmao/agents/launch_policy/registry/codex.yaml`), the shadow TUI parser emits `unknown_version_floor_used` and keeps `surface.ready_posture: "unknown"` even when the pane visibly shows the ready composer (`Ask Codex to do anything`). The registered parser presets only cover 0.1.0 and 0.98.0.

## Scope

Pre-existing parser coverage gap, not caused by the hook observation channel. Hook-driven lifecycle phases (`active`, `blocked`, `ready`) still publish correctly when the channel is active, which masks the gap for opted-in sessions; TUI-only Codex sessions at current versions lack a trustworthy ready-posture signal.

## Candidate Fix

Register a parser preset for the current Codex TUI layout (0.162.x/0.163.x line) using the 2026-10-12 codex TUI parsing campaign recordings (`context/campaigns/debug/2026-10-12-codex-tui-parsing/`, blind-labeled at 0.162.1) plus fresh 0.163.0 captures, and add a version-regression test so a preset gap at the supported floor fails CI.
