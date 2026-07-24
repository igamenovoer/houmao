---
name: houmao-dev-tui-testing
description: Use when a Houmao developer needs to turn an agent TUI task or use case into a replay-grade tmux recording, independently label public tracked states, replay current Claude, Codex, or Kimi detection at varied capture cadences, compare it with ground truth, or render review evidence.
---

# Houmao Development TUI Testing

## Overview

Capture raw terminal evidence before exposing tracker output, then keep every label, replay, comparison, and video traceable to one immutable high-rate recording. Treat manual ground truth and current Houmao state computation as separate evidence lanes until labels are frozen.

## When to Use

Use this skill for development tests of Houmao TUI state detection and transition behavior, especially when a task description must become a reproducible tmux session and replay corpus. It also applies when investigating ready-versus-busy admission, cadence sensitivity, multi-turn transitions, or a detector regression that needs a review video.

Do not use it for ordinary agent work, headless-only tests with no TUI state question, production monitoring, or Gemini CLI testing. This development skill does not define product-facing user workflows.

## Workflow

1. **Resolve the repository, task description, provider, test project, and fresh run root.** Read [references/artifact-contract.md](references/artifact-contract.md).
2. **Select a public subcommand** from **Subcommands** and verify its predecessor artifacts.
3. **Delegate every required agent launch.** Invoke the matching `houmao-dev-launch-agents` provider subcommand and consume its verified tmux session; do not resolve provider credentials, proxy settings, or launch commands in this skill.
4. **Enforce the evidence boundary.** Use only Claude, Codex, or Kimi in unattended mode; freeze the high-rate recording and manual labels before computing tracker output.
5. **Execute the selected subcommand workflow** from its linked command page, using current project interfaces from [references/project-interfaces.md](references/project-interfaces.md).
6. **Verify and report the artifacts.** Include provider/version, delegated launch evidence, recording and label digests, replay cadence and seed, comparison kind, video metadata, incomplete obligations, and exact paths.

If the task does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this skill's subcommands, evidence rules, and artifact contracts, then execute the plan.

## Invocation Contract

These are skill subcommands, not shell commands. Preferred forms are `$houmao-dev-tui-testing use <subcommand> ...` and `$houmao-dev-tui-testing <task>`, where the skill selects the closest subcommand.

## Subcommands

### Procedural Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `record` | Turn a task or use case into an immutable high-rate recording of a TUI launched through `houmao-dev-launch-agents` | [commands/record.md](commands/record.md) |
| `label` | Review raw evidence without tracker output and author complete public-state ground truth | [commands/label.md](commands/label.md) |
| `replay` | Run the current tracker over the source recording and deterministic lower or irregular cadence variants | [commands/replay.md](commands/replay.md) |
| `compare` | Compare replay with ground truth using strict canonical and cadence-aware semantic contracts | [commands/compare.md](commands/compare.md) |
| `render-video` | Produce and verify blind, ground-truth, or detector-comparison review videos | [commands/render-video.md](commands/render-video.md) |

### Helper Subcommands

No helper subcommands are currently exposed.

### Misc Subcommands

| Subcommand | Use For | Detail |
| --- | --- | --- |
| `run-all` | Execute the full evidence workflow in procedural order without crossing the blind-label boundary | [commands/run-all.md](commands/run-all.md) |
| `help` | Explain the invocation contract, public subcommands, predecessor artifacts, and output layout | This entrypoint |

## Non-Negotiable Evidence Rules

- Use `tmp/houmao-dev-tui-testing/<run-id>/` or a more specific user-provided `tmp/<subdir>` for temporary projects and artifacts. Never reuse a non-empty run root.
- Default canonical capture to `0.05` seconds per sample (20 Hz). Freeze and digest `pane_snapshots.ndjson` before labeling or replay.
- `pane_snapshots.ndjson` is machine replay authority. `session.cast` is for human review and input context, not state computation.
- Do not inspect `state_observed*.ndjson`, tracker logs, detector traces, gateway TUI state, or live Houmao tracking while authoring ground truth.
- Ground truth targets the seven public tracked-state fields in [references/state-labeling.md](references/state-labeling.md), not detector internals or deprecated readiness/completion projections.
- Treat a confirmation prompt in an unattended run as a failed or incomplete test unless the upstream CLI hard-codes the intervention and exposes no setting to skip it. Record the exception; do not silently click through it.
- Never add Gemini CLI to the matrix. Route all Claude, Codex, and Kimi launches through `houmao-dev-launch-agents`; provider credentials, launchers, and proxy posture belong to that skill.
- Preserve failed and partial attempts. A rerun gets a new attempt or run root.

## Common Mistakes

- Labeling after reading current tracker output, which turns the implementation under test into its own oracle. Restart labeling from the raw frozen recording with a clean label artifact.
- Using detector-owned `wait_for_ready` or `wait_for_active` gates in a supposedly blind capture. Use fixed waits, direct visible-pattern waits, or recorded operator decisions instead.
- Calling every downsampled field mismatch a bug. Canonical replay is sample-exact; varied-cadence replay is judged by source mapping, transition meaning, admission safety, and bounded timing drift.
- Equating a visible composer with prompt readiness. A CLI may accept typed text while the current turn remains active and would queue a submitted prompt.
- Rendering only an MP4 and discarding the machine evidence. Keep the manifest, timelines, comparison, video metadata, and hashes together.
- Calling a launch-owning demo or provider CLI directly. Delegate launch first, then target the returned tmux pane with the recorder.
