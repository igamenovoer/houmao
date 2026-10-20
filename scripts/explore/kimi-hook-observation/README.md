# kimi-hook-observation harness (throwaway, not production)

Executable tooling for Phase A of the 2026-10-20 Kimi debug campaign at
[`context/campaigns/debug/2026-10-20-kimi-hook-observation/`](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/),
implementing the harness checklist in
[`2026-10-20-plan-1-kimi-hook-capture-matrix.md`](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md).

**Throwaway experiment harness.** Nothing under this directory is production code, and nothing under `src/`, `tests/`, `openspec/`, `context/`, or `tools/` is modified by it. Delete the directory when the campaign closes.

The harness captures Kimi Code hook events from live TUI and headless sessions: a loopback collector receives command-hook POSTs, a generated `$KIMI_CODE_HOME/config.toml` subscribes all 20 events through `[[hooks]]` entries, a one-command runner creates an isolated scratch `KIMI_CODE_HOME` by copying the operator's real home at runtime, launches `kimi` in detached tmux, drives a frozen scenario arm with tracker-blind `tmux send-keys`, records the pane at 5 fps, and writes a labels template plus a secret-free `launch.json` manifest.

The provider-free G0 gate is built in and is the only execution the harness build requires. **Phase A did not launch Kimi; Phase B ran the scenario arms; Phase C replays the captures with `replay_reduce.py`.** The campaign closed on 2026-10-20 with 13 arms / 16 launches and a passing full-matrix replay.

## Layout

| Path | Purpose |
| --- | --- |
| `kimi_hooks.py` | Generate/merge the 20-entry `[[hooks]]` block into a scratch `config.toml`, strict `tomllib` read-back validation, plus the unvalidated raw-append helper for S2/H1 |
| `collector.py` | Stdlib loopback HTTP collector: bearer validation, monotonic sequence stamping, millisecond UTC timestamps, `events.ndjson`, periodic `collector.json` heartbeat, `GET /health` |
| `emit_hook.py` | Command-hook emitter: stdin JSON -> collector POST, file fallback, silent stdout, always exit 0 |
| `run_capture.py` | One-command scenario runner (`s0`-`s9`, `f1`, `d1`, `t1`) plus the provider-free `--self-test` gate G0 |
| `replay_reduce.py` | Stdlib replay reducer: captured `events.ndjson` -> merged posture timeline, expectation and label checks, synthetic `--self-test`, full-matrix `--all` |
| `README.md` | This file |

## Quick start: G0 self-test

Run everything via Pixi from the repository root. `--self-test` starts the collector, posts a synthetic payload with `urllib`, exercises the emitter against a live and a dead collector, generates and strictly validates a hooks config (including a duplicate entry), verifies the malformed-entry helper writes without validation, and confirms the installer guard refuses the malformed section. It never launches Kimi and needs no credentials.

```bash
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --self-test
```

Expected tail: `SELF-TEST PASSED` with exit code 0.

The config helper can also be exercised directly:

```bash
pixi run python scripts/explore/kimi-hook-observation/kimi_hooks.py \
  --config /path/to/scratch/config.toml --validate --require-all-events
```

## Scenario usage

Every scenario runs unattended with bounded waits and tears down tmux, the pane recorder, and the collector in a `finally` block, including aborts. Default run root: `tmp/kimi-hook-capture/<scenario>/run-<UTCts>/`; override with `--run-root <dir>`. The Kimi binary defaults to `kimi` on `PATH`; the seed source defaults to `~/.kimi-code`. Both are overridable with `--kimi-binary` and `--kimi-home-source`.

```bash
# S0 gate: --auto TUI, 20 hooks, expect SessionStart before any prompt.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s0

# S1 normal: OK turn, echo-hi turn, >=65 s heartbeat hold, mid-session H1 marker.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s1

# S2 malformed control: one extra `cwd` key kills the whole hooks section, plus
# a paired `kimi -p` stderr probe for the config warning.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s2

# S3 permission lane: no --auto, approve once and deny once. The driver reads
# the approval panel's numbered options at runtime and records the keys used.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s3

# S4 manual compaction: README turn, /compact, post-compact OK turn.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s4

# S5 Esc interrupt mid-generation.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s5

# S6 second prompt typed while the first turn is busy.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s6

# S7 clean exit, append the H1 marker hook, then `kimi --continue` on the same home.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s7

# S8 headless: KIMI_CODE_HOME=<scratch> kimi -p "Reply with exactly: OK"; no tmux.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s8

# F1 fault: kill -9 the Kimi process tree mid-turn.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario f1

# D1 transport fault: kill the collector after SessionStart, one OK prompt.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario d1

# T1 slow lifecycle: SessionStart/SessionEnd prefixed with `sleep 3`, no prompt.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario t1

# S9 optional subagent arm.
pixi run python scripts/explore/kimi-hook-observation/run_capture.py --scenario s9
```

`t1` compares its ready/exit timings against the newest `s0` `launch.json` under `tmp/kimi-hook-capture/s0/`. Run S0 first or accept `null` deltas.

## Replay phase usage

`replay_reduce.py` is the Phase C (E3/E4) reducer. It is stdlib-only, deterministic (ordering and virtual time come from the stream's own `received_at_monotonic` / `received_at_utc` stamps; no wall clock is read), and imports no production code. It reduces a run root's `collector/events.ndjson` to a merged posture timeline: session generation/presence, turn busy/settle, blocked window, interrupted, compaction hold, subagent scope, heartbeat liveness, and terminal-gap/headless fallbacks. Fallback rows (`"sequence": null`, `"via": "command_fallback"`) are ordered by `emitter_seq`; HTTP and fallback counters are deduplicated independently.

```bash
# Synthetic reducer checks: normal, blocked allow, blocked deny, compaction,
# interrupt, terminal gap, resume generation, headless-no-SessionEnd, queue,
# subagent scope, fallback ordering, and fallback loader ordering.
pixi run python scripts/explore/kimi-hook-observation/replay_reduce.py --self-test

# Replay every campaign run root under tmp/kimi-hook-capture/ and check the
# declared stream shape, final posture, counters, and filled labels. Harness
# G0 self-test roots are detected as non-campaign streams and named as skipped.
pixi run python scripts/explore/kimi-hook-observation/replay_reduce.py --all

# One run root with a per-event timeline (useful while inspecting a new arm).
pixi run python scripts/explore/kimi-hook-observation/replay_reduce.py \
  --run-root tmp/kimi-hook-capture/s3/run-20261020T133622Z

# Skip label checks when the labels file is still empty.
pixi run python scripts/explore/kimi-hook-observation/replay_reduce.py --all --no-labels
```

The reducer encodes the kimi-specific rules the capture phase established: `turn_id` is absent on tool events (tool calls correlate by stream order), `UserPromptSubmit` arms an epoch and `TurnStarted(origin_kind=user)` binds it, nested `TurnStarted(origin_kind=system_trigger)`/`SubagentStart` scopes consume their own `Stop`, `PermissionRequest` enters `blocked` and `PermissionResult` settles it (not `PostToolUse`), deny continues to a normal `Stop`, `PreCompact`/`PostCompact` hold posture, `Interrupt` settles `interrupted`, and a stream that ends with an open turn is a terminal gap. S7 generation 2 starts at `turn_id=1` (the session-scoped counter continues across resume). Headless `-p` with an rc-0 exit and a latched `Stop` is terminal-settled; the missing `SessionEnd` is named `headless_session_end_gap`.

Exit codes: `--self-test` returns 0 only when all synthetic checks pass; `--all` returns 0 only when every expectation and label check passes. Run both via `pixi run` so the managed interpreter is used. `--all` reads run metadata from `launch.json` / `run-summary.json` for headless and return-code detection; a bare `--run-root` with no metadata still reduces the stream but cannot distinguish a clean headless exit from a silent stop.

## Artifact layout per run

```text
tmp/kimi-hook-capture/<scenario>/run-<UTCts>/
  launch.json                      # versions, flags, ports, paths, UTC/monotonic pairs, TUI surface constants
  launch-wrapper-gen<N>.sh         # mode 0600; exports KIMI_CODE_HOME and HOUMAO_HOOK_*, execs kimi
  driver-input-events.ndjson       # every driver action, ts_utc + monotonic
  raw-provider-payloads.ndjson     # pristine provider payloads in receive order (payload catalog input)
  run-summary.json                 # event counts/ordering, timings, permission evidence, notes, abort status
  s2-print-probe.{stdout,stderr}.txt  # S2 only: headless config-warning probe
  s8-headless.{stdout,stderr}.txt     # S8 only: headless run capture
  kimi-home/
    config.toml                    # seeded copy + 20 [[hooks]] entries (+ S2 malformed / H1 marker when applicable)
    credentials/ oauth/ device_id  # copied at runtime; never read, hashed, or printed by the harness
    workspace-trust/wd_<slug>_<hash12>  # pre-seeded trust record
  workdir/                         # git-less scratch cwd (s4 gets a small README.md)
  collector/
    events.ndjson                  # one envelope per event (sequence, received_at_utc ms,
                                   #   received_at_monotonic, channel_generation, via, delivery, provider_event)
    collector.json                 # heartbeat/health: status, pid, port, counts, last heartbeat UTC/monotonic
    collector.json.gen<N>          # archived status per collector generation
    collector-gen<N>.log           # collector stderr (event/size/seq/outcome lines)
    emitter.log                    # emitter stderr (bounded ~1 MiB)
    .emitter-seq                   # cross-process client sequence counter
  pane-recording/                  # 5 fps recorder run (s7: pane-recording-resume/ too)
  labels/labels-template.json      # predeclared expectation + empty timestamped slots
  notes/                           # visible-pane snapshots (bootstrap, trust, permission, resume, S2 probe)
```

HTTP envelopes carry integer `sequence`; file-fallback envelopes written by `emit_hook.py` carry `"sequence": null` and `"via": "command_fallback"`, so consumers must tolerate a null sequence. The collector resumes `sequence` from the existing `events.ndjson` on restart, so S7's second generation continues the run sequence. `collector.json` counts cover only collector-accepted events for the current generation.

## Collector and emitter design

- **Ack-before-disk.** The HTTP handler validates the bearer token, payload size, and JSON, enqueues `(payload, delivery metadata, receive stamps)`, and returns 204. One writer thread assigns the per-run monotonic `sequence` and appends to `events.ndjson`. A collector crash can lose an already-acked event; the campaign accepts that for low hook latency.
- **Millisecond UTC.** `received_at_utc` uses `timespec="milliseconds"`; per-event `received_at_monotonic` shares the system monotonic clock with the runner and recorder, so pane frames align without a wall-clock conversion.
- **Heartbeat file.** `collector.json` is written on start, after every accepted event, on a fixed interval (default 2 s), and on shutdown. `last_heartbeat_monotonic` lets a watcher detect collector death; the file is secret-free.
- **Pristine payloads.** The emitter does not inject stamps into the provider payload. Event name and client sequence travel as `?event=<name>&seq=<n>` and `X-Hook-Event` / `X-Hook-Seq` headers; the collector records them under `delivery`. Kimi payloads already carry `hook_event_name`, but the header path is kept for parity with the Claude and Codex lanes.
- **Emitter contract.** Read stdin to EOF, POST with a 1.5 s timeout (below the 5 s hook timeout), append to the run's `events.ndjson` on any failure, print nothing to stdout, always exit 0, and send stderr to a bounded log. The fallback envelope stamps `channel_generation`, `via: "command_fallback"`, a run-local flock `emitter_seq`, and `"sequence": null`.

## Hooks injection shape

- All 20 events are subscribed: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, `PermissionResult`, `UserPromptSubmit`, `UserPromptQueued`, `TurnStarted`, `Stop`, `StopFailure`, `Interrupt`, `SessionStart`, `SessionEnd`, `SessionHeartbeat`, `SubagentStart`, `SubagentStop`, `TaskStarted`, `PreCompact`, `PostCompact`, `Notification`.
- Each entry carries only `event`, `command`, and `timeout = 5`; `matcher` is omitted (match all). Kimi's strict schema allows only `{event, matcher, command, timeout}`, and one extra key drops the entire hooks section with a warning only.
- The command is `<pixi python> <abs emit_hook.py>`, POSIX shell-quoted. Kimi executes hook commands through the system shell with cwd = session project dir and stdin = one JSON object without a trailing newline.
- The merge appends a marker-delimited block and verifies byte-for-byte that the seeded config's prefix is untouched. The file is parsed back with `tomllib`; every entry is checked against the key whitelist, the 20-name event enum, and an integer timeout in `1..600`. Any violation restores the original file and raises before a launch.
- S2 appends one extra entry with `cwd = "/tmp"` through `append_raw_toml_block()`; S1/S7 append a `UserPromptSubmit` marker hook the same way. Both deliberately bypass the installer guard so the campaign can observe the runtime failure modes.

## Workspace trust seeding

Kimi checks a presence-only per-workspace trust record at `$KIMI_CODE_HOME/workspace-trust/<encodeWorkDirKey(cwd)>`. The harness mirrors Houmao's production projection (`src/houmao/agents/kimi_workspace_trust.py`): `encodeWorkDirKey` normalizes slashes, slugifies the basename (lowercase, `[a-z0-9._-]`, max 40 chars), and appends the first 12 hex characters of SHA-256 over the normalized path. The record is compact JSON `{"root": "<absolute workdir>", "trustedAt": <epoch ms>}`, mode 0600. The trust modal should therefore never paint; if it does, `bootstrap_session()` aborts and saves a pane snapshot. The `KIMI_CODE_TRUST_WORKSPACE=1` environment fallback is intentionally not used so the record shape itself is tested.

## Discovered Kimi TUI surfaces (docs/source, 2026-10-20)

These are constants at the top of `run_capture.py` so Phase B can correct them after the S0 gate without touching scenario logic.

- **Ready composer.** Kimi's welcome box renders `Welcome to Kimi Code!` and `Directory: <cwd>`; the footer renders `context: N% (...)` and the editor draws long `─` borders. Kimi 2.2.0 renders the TUI **inline from the top of the pane** (the ready surface occupies roughly the first 22 rows of a 56-row pane, with blank rows below), so readiness scans the whole visible pane for the footer plus one companion marker, held stable for 2 s. Source: `apps/kimi-code/src/tui/components/chrome/welcome.ts`, `footer.ts`, and `packages/pi-tui/src/components/editor.ts`. Live correction 2026-10-20: a last-10-lines footer scan produced two false negatives at S0.
- **Exit.** `/exit` (aliases `/quit`, `/q`), idle-only. Documentation: `docs/en/reference/slash-commands.md`. The fallback sequences are double `Ctrl-C` and double `Ctrl-D`, both documented as a two-press confirmation (`docs/en/reference/keyboard.md`). The successful path and duration are recorded in `run-summary.json` and `launch.json`.
- **Permission panel.** Headers are `Run this command?` (Bash), `Write this file?` (Write), `Apply these edits?` (Edit), `Stop this task?`, `Ready to build with this plan?`, and `Approve <tool>?` by default. Options render as numbered lines `1. <label>` with a `▶` selection marker; the keyboard reference documents `↑`/`↓`, `Enter`, `1`–`9`, and `Esc`/`Ctrl-C`/`Ctrl-D` as reject. The driver parses the numbered options from the pane, sends the index of the first label containing `Approve`, and records the detected labels and chosen key. Deny uses `Escape`, which rejects directly and avoids the feedback-input state that a `Reject` option may enter.
- **Trust modal.** `Trust this folder?`, options `Trust and continue` / `Exit`, footer `↑↓ navigate · Enter select · Esc exit`. Source: `apps/kimi-code/src/tui/components/dialogs/trust-prompt.ts`.
- **Busy state.** There is no stable textual busy marker in the TUI source comparable to Codex's `esc to interrupt`. S5/S6 wait for `TurnStarted` and then hold a fixed 2–3 s before acting; the resulting event stream is the source of truth.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `HOUMAO_HOOK_COLLECTOR_URL` | Collector endpoint exported by the wrapper (for example `http://127.0.0.1:<port>/v1/hook`) |
| `HOUMAO_HOOK_TOKEN` | Per-run bearer token exported by the wrapper; never embedded in `config.toml` or `launch.json` |
| `HOUMAO_HOOK_STORE` | Run artifact directory for the fallback `events.ndjson` and `.emitter-seq` |
| `HOUMAO_HOOK_GENERATION` | Collector generation stamped into fallback envelopes |

Each emitter variable has a matching CLI flag for manual runs. The collector itself takes `--store`, `--token`, `--generation`, `--port` (0 picks an ephemeral loopback port), and `--heartbeat-seconds`.

The wrapper also exports `KIMI_CODE_HOME=<scratch>` and `KIMI_CODE_NO_AUTO_UPDATE=1` for version pinning.

## Differences from the Codex harness

- **No credential launcher or profile template.** Kimi reads its own home directly; the wrapper only exports `KIMI_CODE_HOME` and the hook environment. The real `~/.kimi-code` is copy-from only.
- **No hook trust hash.** Kimi has no hook trust gate; `hash_hook.py` has no counterpart. The workspace-trust record is pre-seeded instead.
- **TOML `[[hooks]]` instead of `hooks.json`.** One entry per event, no matcher, timeout 5 for every event (Kimi has no SessionEnd clamp). `kimi_hooks.py` owns the strict read-back guard.
- **Stdlib-only tmux.** `run_capture.py` calls the `tmux` binary directly instead of importing Houmao's `run_tmux`, keeping the harness dependency-free.
- **Scenario mapping.** S2 is the malformed-config control (not trust); S3 is ask-mode permissions; S8 is headless; D1 is the transport fault; T1 is slow lifecycle hooks; S9 is optional. There is no `t2` session-flag arm because Kimi only reads hooks from `config.toml`.
- **Permission keys are runtime-discovered.** The Codex lane hardcodes `y`/Escape; the Kimi lane parses the panel's numbered options and records what it found.
- **Readiness detection is Kimi-specific** (welcome box + footer + editor border) rather than Codex's composer glyph.
- **Self-test uses `urllib`** instead of shelling out to `curl`, and adds TOML guard checks (duplicate passes, malformed refused, unknown event refused).

## Known limitations and deferred checks

- No live Kimi session is started in Phase A. Every surface string above is docs/source-derived; the S0 gate is the first live correction point.
- Dedup of identical `(cwd, command)` hooks is verified live: the S0 scratch home carries 21 entries (20 events plus a duplicate `UserPromptSubmit`) and one prompt produced exactly one delivery. `run_s0()` records `g1.user_prompt_submit_deliveries` and `g1.dedup_holds`.
- **Session-less TUI startup (2026-10-20).** At kimi 2.2.0 the TUI starts with no session (`No session yet — one will be created on your first message.`) and creates it on the first submitted message. G1 was amended accordingly: the frozen prompt creates the session, then `SessionStart` must arrive within 15 s and before the turn's `UserPromptSubmit`/`Stop`. Every fresh-session scenario submits its first frozen prompt before requiring `SessionStart`; S7's resume is the exception because `--continue` creates at launch.
- Plain `Enter` while a turn is busy buffers in the composer and submits after `Stop`; it does **not** emit `UserPromptQueued`. The S6 steer path uses `Ctrl-S` and produces `UserPromptQueued` with no second `UserPromptSubmit`/`Stop`.
- `turn_id` is a session-scoped integer that continues across `--continue` (S7 generation 2 starts at 1), and it collides across parent/subagent scopes (S9: both 0). Correlate tool events by stream order; correlate subagent turns by `SubagentStart`/`SubagentStop` and scope, not by `turn_id` alone.
- Headless `kimi -p` emits `SessionStart`/`UserPromptSubmit`/`TurnStarted`/`Stop` but no `SessionEnd` at 2.2.0; process exit is the terminal signal.
- T1 now sends one short OK prompt to create the session; the arm is no longer zero-model-cost, and the slow `SessionStart` hook delays session creation, not the ready composer.
- S3's approve key is discovered from the pane; if the panel labels do not contain `Approve`, the driver falls back to key `1` and records the deviation. Deny always uses `Escape`.
- There is no stable TUI busy marker, so S5/S6 use `TurnStarted` plus a fixed delay. If a provider finishes the essay before the delay, `Interrupt` will be absent and the run records that rather than forcing a fault.
- The S2 paired `kimi -p` probe makes one short model call. The intent's "zero token" note may have assumed the warning can be observed without a turn; if cost matters, replace the probe prompt with a config-only invocation once one is found.
- The harness copies Kimi's own credential files but does not synthesize provider environment variables. The operator's provider configuration must already authenticate for `kimi` in the runner's environment.
- Workspace-trust canonicalization may differ on symlinked paths. The harness resolves the workdir with `Path.resolve()` and aborts with a pane snapshot if the modal still paints.
- T1 needs a prior S0 run for the delay comparison; without one it records absolute timings and `null` deltas.
- The collector uses ack-before-disk, so a crash between the 204 response and the writer append loses that event. This is the accepted latency trade.
- The collector accepts only `Content-Length` POSTs and caps payloads at 1 MiB; chunked and oversized requests are rejected.
- `SessionHeartbeat` fires only when the event is configured (it is) and runs on a 60 s timer; S1 holds the session for at least 70 s from launch.
- The hook command embeds the absolute Pixi Python path. That interpreter must remain resolvable for the whole campaign.
- Scratch homes and run roots may contain credential material and prompt text; `tmp/kimi-hook-capture/` is sensitive campaign evidence and stays gitignored.
- The pane pid is killed as a whole descendant tree in F1 to avoid orphaning child processes; the pane recording may end with a pane-resolution failure, which is the expected terminal-gap signature.

## Links

- Campaign intent: [`debug-intent.md`](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/debug-intent.md)
- Iteration plan: [`2026-10-20-plan-1-kimi-hook-capture-matrix.md`](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/iterations/2026-10-20-plan-1-kimi-hook-capture-matrix.md)
- Key questions: [KQ-1](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/key-questions/KQ-1-config-injection-coexistence.md), [KQ-3](../../../context/campaigns/debug/2026-10-20-kimi-hook-observation/key-questions/KQ-3-delivery-semantics.md)
