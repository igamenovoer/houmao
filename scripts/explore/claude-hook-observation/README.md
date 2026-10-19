# claude-hook-observation harness (throwaway, not production)

Executable tooling for the 2026-10-19 debug campaign at
[`context/campaigns/debug/2026-10-19-claude-hook-observation/`](../../../context/campaigns/debug/2026-10-19-claude-hook-observation/),
implementing the harness checklist in
[`2026-10-19-plan-1-hook-capture-matrix.md`](../../../context/campaigns/debug/2026-10-19-claude-hook-observation/iterations/2026-10-19-plan-1-hook-capture-matrix.md)
against the design contract in
[`claude-hook-adapter.md`](../../../context/features/2026-10-18-cli-hook-observation-channel/design/claude-hook-adapter.md)
(sections 2.3, 2.4, 2.5, and 3).

**Throwaway experiment harness.** Nothing under this directory is production
code, and nothing under `src/`, `tests/`, `openspec/`, `context/`, or `tools/`
is modified by it. Delete the directory when the campaign closes.

The harness captures Claude Code hook events from live TUI sessions: a
loopback collector receives HTTP hook events, a command-hook emitter covers
`SessionStart` (which supports no HTTP hook), a generated session-scoped
`--settings` file wires the hooks up, and a one-command runner launches
claude in detached tmux, drives a frozen scenario arm with tracker-blind
`tmux send-keys`, records the pane at 5 fps, and writes label templates.

## Layout

| Path | Purpose |
| --- | --- |
| `observer_settings.py` | Generate the secret-free session-scoped observer settings JSON (v1 event set, 9 events) |
| `collector.py` | Stdlib loopback HTTP collector: bearer validation, sequence stamping, `events.ndjson`, `channel.json`, `GET /health` |
| `emit_hook.py` | Command-hook emitter: stdin JSON -> collector POST, file fallback, silent stdout, always exit 0 |
| `run_capture.py` | One-command scenario runner (`--scenario s0..s7, s1-control`) plus the provider-free `--self-test` gate G0 |
| `README.md` | This file |

## Usage

Run everything via Pixi from the repository root. The only execution you
should perform while building/verifying the harness is the self-test; live
scenario runs belong to the campaign execution checklist.

```bash
# Gate G0: provider-free harness self-test (synthetic POST, emitter POST,
# emitter file fallback, wrong-token rejection).
pixi run python scripts/explore/claude-hook-observation/run_capture.py --self-test

# Home-injection coexistence arm (iteration-1 addendum): observer block merged
# into a scratch managed home's settings.json via CLAUDE_CONFIG_DIR; no
# --settings is passed, and a dummy operator hook must keep firing.
pixi run python scripts/explore/claude-hook-observation/run_capture.py \
  --scenario s1 --inject-via home

# Gate G1 smoke: S0 (observer settings + skip-permissions launcher).
pixi run python scripts/explore/claude-hook-observation/run_capture.py --scenario s0

# Permissions lane S3 (launcher env replicated inline, NO --dangerously-skip-permissions).
pixi run python scripts/explore/claude-hook-observation/run_capture.py --scenario s3

# Queue + resume lane S7 (second launch with --resume; collector generation bump).
pixi run python scripts/explore/claude-hook-observation/run_capture.py --scenario s7
```

Every scenario runs unattended with bounded waits and tears down tmux, the
pane recorder, and the collector in a `finally` block, including aborts. A
failed model gate (the TUI must show `DeepSeek Flash` before any prompt is
sent) aborts the run and records the reason.

Default run root: `tmp/hook-capture/<scenario>/run-<UTCts>/`; override with
`--run-root <dir>`.

## Artifact layout per run

```text
tmp/hook-capture/<scenario>/run-<UTCts>/
  launch.json                      # tmux session/pane/pid, timestamps, monotonic base
  launch-wrapper-gen<N>.sh         # mode 0600; exports HOUMAO_HOOK_TOKEN, execs launcher
  observer-settings-gen<N>.json    # secret-free; SessionStart command + 8 HTTP hooks
  driver-input-events.ndjson       # every driver action, ts_utc + monotonic
  run-summary.json                 # event counts/ordering, notes, abort status
  workdir/                         # git-less scratch cwd (s4 gets a small README.md)
  collector/
    events.ndjson                  # one envelope per event (sequence, received_at_utc,
                                   #   channel_generation, via, provider_event)
    channel.json                   # secret-free status incl. started_monotonic UTC pair
    collector-gen<N>.log           # collector stderr (event/size/seq/outcome lines)
    emitter.log                    # command-hook emitter stderr (bounded ~1 MiB)
  pane-recording/                  # 5 fps recorder run (s7: pane-recording-resume/ too)
  labels/labels-template.json      # predeclared expectation + empty timestamped slots
  notes/                           # visible-pane snapshots (permission/resume surfaces)
```

Collector envelopes from HTTP delivery have integer `sequence`; file-fallback
envelopes (collector unreachable, written by `emit_hook.py`) carry
`"sequence": null` and `"via": "command_fallback"`, so consumers must
tolerate a null sequence. `channel.json` counts only cover collector-accepted
events; fallback appends are visible in `events.ndjson` only.

## Observer settings shape (what is generated)

Design 2.3 forbids HTTP handlers for `SessionStart`, so the v1 event set is:

- `SessionStart` -> `{"type": "command", "command": "<abs emit_hook.py>", "timeout": 2}`
- `UserPromptSubmit`, `Stop`, `StopFailure`, `PermissionRequest`,
  `PreCompact`, `PostCompact`, `PostToolUse`, `PostToolUseFailure`
  -> `{"type": "http", "url": "http://127.0.0.1:<port>/v1/hook", "timeout": 2,
  "headers": {"Authorization": "Bearer $HOUMAO_HOOK_TOKEN"},
  "allowedEnvVars": ["HOUMAO_HOOK_TOKEN"]}`

The settings file is secret-free: the bearer token appears only as the
literal env reference `$HOUMAO_HOOK_TOKEN` (design 2.5). The actual token is
generated per run by `run_capture.py` and lives only in the mode-0600 launch
wrapper's environment, plus the collector's `--token` argument. The wrapper
also exports `HOUMAO_HOOK_COLLECTOR_URL`, `HOUMAO_HOOK_STORE`, and
`HOUMAO_HOOK_GENERATION` for the emitter.

## Injection modes

- `--inject-via settings` (default): session-scoped `claude --settings
  <observer.json>` (design 2.1).
- `--inject-via home` (iteration-1 addendum, home-injection coexistence arm):
  the wrapper exports `CLAUDE_CONFIG_DIR=<run-root>/claude-home` and passes
  **no** `--settings`. The scratch home mimics the managed-home bootstrap
  (`settings.json` with `skipDangerousModePermissionPrompt: true`,
  `.claude.json` with `hasCompletedOnboarding`/`numStartups`), and the
  observer block is marker-merged into the home `settings.json` together with
  a dummy operator `UserPromptSubmit` hook (design 2.2 fallback, tested as a
  primary path). The operator hook appends to
  `operator-hook-marker.txt` in the run root; S1's two prompts must produce
  exactly two marker lines.

## Credential hygiene

- `~/.local/bin/deepseek-api-key` and `DEEPSEEK_API_KEY` are never read,
  printed, copied, or embedded by this harness. The normal lane execs
  `~/.local/bin/claude-deepseek` as-is; the s3 lane's generated wrapper reads
  the key at runtime inside the pane shell (same mechanism as the launcher).
- Only the token env name appears in artifacts; the per-run hook token is
  embedded solely in the mode-0600 wrapper.
- The s3 lane pins `--permission-mode manual`: without it, 2.1.303 boots the
  no-bypass lane into `auto` mode, which auto-allows tool calls (no modal, no
  `PermissionRequest`) — observed and recorded 2026-10-19.
- `events.ndjson` may contain prompt text and tool payloads from the
  provider; treat run roots as sensitive campaign evidence.

## Boundaries

- Harness code is stdlib-only (plus the repo's `run_tmux` helper import).
- `s1-control` launches with no `--settings` (hooks off) as the P2.3 matched
  control and records pane-settle wall-clock timings instead of events.
- `SessionEnd` is deliberately not subscribed in the v1 event set (design P2
  optional); s1 records its absence post-exit.
