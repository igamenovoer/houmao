# KQ-1: Config Injection and Coexistence

Status: answered (2026-10-20); named unresolved items remain where marked. Owner: iteration 1. Campaign: [debug-intent.md](../debug-intent.md).

## Question

Can houmao's observer hooks be injected as `[[hooks]]` entries into a scratch `KIMI_CODE_HOME/config.toml` such that they execute with zero user action in unattended `--auto` TUI mode, and what are the exact failure modes of that injection? Unlike Codex (trust hash) there is no trust gate to defeat (source-settled); the kimi-specific injection risks are the strict schema's silent section-drop, the load-once hook table, and coexistence with fields houmao's launch policy already owns in the same file.

Source baseline: strict schema at `extern/orphan/kimi-code/packages/agent-core-v2/src/features/externalHooks/configSection.ts:10-17` (@ `67325c1`); section-drop-with-warning at `app/config/configService.ts:739-758`; load-once at `app/externalHooksRunnerService.ts:37-41`; houmao-owned fields at `src/houmao/agents/launch_policy/registry/kimi.yaml:42-52,104-110`.

## Propositions

### P1.1 Seeded scratch home + merged hooks runs unattended

A scratch `KIMI_CODE_HOME` seeded by copying `config.toml`, `credentials/`, `oauth/`, `device_id` from the operator's real home at runtime, then merged with 20 `[[hooks]]` observer entries, launches `kimi --auto` in tmux with hooks firing and zero interactive prompts (no modal, no trust screen, no migration prompt). Test: S0; record time from launch to ready composer and to `SessionStart`. Also verify `KIMI_CODE_NO_AUTO_UPDATE=1` keeps the binary at 2.2.0 for the campaign's duration.

### P1.2 One malformed entry voids the whole section, warning only

Adding one `[[hooks]]` entry with an extra key (for example `cwd = "/tmp"`) causes the CLI to drop the *entire* hooks section with a warning diagnostic — no error, no nonzero exit; the observation channel is silently dead. Test: S2 control; record exactly where the warning is visible (print-mode stderr per `run-v2-print.ts:206-210`; TUI surface unknown — capture what the TUI shows) and confirm no hook fires. This is the failure mode the production installer must detect after writing.

### P1.3 The hook table is load-once

Appending a new `[[hooks]]` entry to a running session's `config.toml` has no effect until the process restarts. Test: fold into S1/S7 — append a marker hook (`UserPromptSubmit` → `touch <marker>`) mid-session, submit a prompt, observe the marker absent; relaunch on the same home (S7), submit a prompt, observe the marker present.

### P1.4 Hooks coexist with launch-policy-owned fields

The observer `[[hooks]]` merge leaves existing `config.toml` content (`default_model`, `[thinking]`, `[secondary_model]`, `[providers.*]`, `[models.*]`) byte-identical outside the appended block, and a subsequent launch-policy-style field write (for example setting `default_permission_mode`) leaves the `[[hooks]]` block intact. Test: diff the seeded config before/after hook merge in S0; perform one field write and re-diff. The TOML merge shape that survives both directions is recorded as evidence for the future production installer.

## Answer

(2026-10-20, amended gate executed. Evidence: [S0 gate smoke](../evidences/2026-10-20-s0-gate-smoke.md), [S2 malformed control](../evidences/2026-10-20-s2-malformed-control.md), [S1 normal](../evidences/2026-10-20-s1-normal-multiturn.md), [S7 resume/hot-reload](../evidences/2026-10-20-s7-resume-hot-reload.md), [S3 permission lane](../evidences/2026-10-20-s3-permission-lane.md), [payload catalog](../evidences/2026-10-20-kimi-hook-payload-catalog.md).)

- **P1.1 — confirmed.** A scratch `KIMI_CODE_HOME` seeded by copying the operator's real home and merged with the 20 `[[hooks]]` observer entries launches `kimi --auto` in tmux with hooks firing and zero interactive prompts. The S0 gate passed under the amended criterion: ready composer 3.219 s with zero keypresses; after the frozen prompt, `SessionStart(source=startup)` arrived 0.238 s later, before `UserPromptSubmit` and `Stop`. All 13 arms ran unattended; no trust modal or migration prompt appeared. `KIMI_CODE_NO_AUTO_UPDATE=1` kept the binary at 2.2.0.
- **P1.2 — confirmed.** S2 added one `[[hooks]]` entry with an extra `cwd` key. The entire hooks section was dropped: zero events in both the TUI turn and a paired `kimi -p` probe. The TUI showed **no warning surface**; print-mode stderr showed `Warning: Ignored invalid config section 'hooks'` with `unrecognized_keys: ["cwd"]` at entry index 20. The session itself was normal (OK answer, rc 0). An installer must detect this by strict read-back, because the TUI operator cannot see it.
- **P1.3 — confirmed.** S1 appended a `UserPromptSubmit` marker hook mid-session; the third prompt produced `UserPromptSubmit` but the marker file stayed absent (load-once holds). S7 appended the same marker between generations and relaunched with `kimi --continue`; the marker fired on the post-resume prompt. Hooks load once per process and require a restart.
- **P1.4 — partially confirmed.** The merge left the seeded config prefix byte-identical and strict read-back passed; `kimi doctor config` returned `OK` for the 21-entry S0 config. S3 performed a launch-policy-style `default_permission_mode = "manual"` write **before** the hook merge and the hooks still ran, so the pre-merge field write coexists. The reverse order (write a launch-policy field **after** the hook block and re-read) was not exercised; that sub-check remains unresolved, though the TOML append shape makes it a formatting-risk rather than a schema-risk.

Injection verdict: append the marker-delimited `[[hooks]]` block to `$KIMI_CODE_HOME/config.toml`, validate by strict read-back, and never rely on a TUI warning. The TUI lane creates the session lazily on the first message, so `SessionStart` is a session-create health signal, not a launch-time one; only a resumed (`--continue`) launch creates at process start.

## Scope

Covers injection mechanics and failure modes only. Event payloads are KQ-2; delivery is KQ-3. The production installer's integration with houmao's launch policy is the future OpenSpec change's scope; this campaign only records the merge shape that works. Evidence: `evidences/` links added as produced.
