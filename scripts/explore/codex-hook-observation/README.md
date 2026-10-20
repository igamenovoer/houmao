# codex-hook-observation harness (throwaway, not production)

Executable tooling for the 2026-10-20 Codex debug campaign at
[`context/campaigns/debug/2026-10-20-codex-hook-observation/`](../../../context/campaigns/debug/2026-10-20-codex-hook-observation/),
implementing the harness checklist in
[`2026-10-20-plan-1-codex-hook-capture-matrix.md`](../../../context/campaigns/debug/2026-10-20-codex-hook-observation/iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md).

**Throwaway experiment harness.** Nothing under this directory is production code, and nothing under `src/`, `tests/`, `openspec/`, `context/`, or `tools/` is modified by it. Delete the directory when the campaign closes.

The harness captures Codex hook events from live TUI sessions: a loopback collector receives command-hook POSTs, a generated `$CODEX_HOME/hooks.json` subscribes all 14 events, a one-command runner creates an isolated scratch `CODEX_HOME`, launches Codex in detached tmux through the `codex-gac` credential lane, drives a frozen scenario arm with tracker-blind `tmux send-keys`, records the pane at 5 fps, and writes a labels template plus a `launch.json` manifest.

The provider-free G0 gate is built in and is the only execution the harness build requires. Live captures belong to the campaign execution checklist.

## Layout

| Path | Purpose |
| --- | --- |
| `observer_hooks.py` | Generate `$CODEX_HOME/hooks.json` for all 14 events, plus the scratch home's `config.toml` (project trust preseed, notice suppression) |
| `collector.py` | Stdlib loopback HTTP collector: bearer validation, monotonic sequence stamping, millisecond UTC timestamps, `events.ndjson`, periodic `collector.json` heartbeat, `GET /health` |
| `emit_hook.py` | Command-hook emitter: stdin JSON -> collector POST, file fallback, silent stdout, always exit 0 |
| `hash_hook.py` | Local reimplementation of Codex's normalized hook trust hash and `[hooks.state."<key>"]` block emitter |
| `run_capture.py` | One-command scenario runner (`s0`-`s7`, `f1`, `t1`, `t2`) plus the provider-free `--self-test` gate G0 |
| `replay_reduce.py` | Stdlib replay reducer: captured `events.ndjson` -> merged posture timeline, expectation checks, label checks, synthetic `--self-test` |
| `README.md` | This file |

## Quick start: G0 self-test

Run everything via Pixi from the repository root. `--self-test` starts the collector, posts with curl, exercises the emitter against a live and a dead collector, validates the generated observer configuration, and runs the hash fixture checks. It never launches Codex and needs no credentials.

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py --self-test
```

Expected tail: `SELF-TEST PASSED` with exit code 0. Individual hash checks are also available directly:

```bash
pixi run python scripts/explore/codex-hook-observation/hash_hook.py --self-test
```

## Scenario usage

Every scenario runs unattended with bounded waits and tears down tmux, the pane recorder, and the collector in a `finally` block, including aborts. Default run root: `tmp/codex-hook-capture/<scenario>/run-<UTCts>/`; override with `--run-root <dir>`.

```bash
# S0 gate: all 14 hooks declared, hook-trust bypass, no pre-trust.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s0

# S1 normal: OK turn, then a tool-using turn (apply_patch + shell), clean exit.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s1

# S2 trust control: hooks present but no bypass and no pre-trust. The run
# records the trust modal (or silent skip) and aborts before prompting unless
# --interactive-trust is given.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s2

# S3 permission lane. Refuses to run with the default codex-gac launcher; see
# "Permission lane limitation" below.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s3 \
  --launcher ~/.local/bin/<gac-launcher-without-approvals-bypass> --allow-permission-lane

# S4 manual compaction via /compact.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s4

# S5 Esc interrupt mid-generation.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s5

# S6 queued/steered input while busy.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s6

# S7 exit, then relaunch with `codex resume <session_id>` on the same scratch home.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s7

# F1 fault: kill -9 the codex process tree mid-turn.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario f1

# T1 pre-trusted hash arm: 14 [hooks.state] entries in config.toml, NO bypass flag.
# After the OK turn, the runner perturbs only the SessionStart command in place
# (same path, same trusted hash), relaunches, and records the trust modal.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario t1

# T2 session-flags arm: `-c hooks.<Event>=[...]` only, no hooks.json, with bypass.
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario t2
```

Every arm except `s2` and `t1` passes `--dangerously-bypass-hook-trust` through the launcher. The default launcher is `codex-openlux-auto` (lane `openlux-auto`); `--launcher ~/.local/bin/codex-gac` selects the GAC profile, and `--lane gac` selects GAC for a custom launcher name. Both credential launchers hardcode `--dangerously-bypass-approvals-and-sandbox`; the S3 permission lane requires a custom launcher that does not.

**SessionStart timing.** Codex 0.163 queues the startup `SessionStart` source at session creation and dispatches it from `run_pending_session_start_hooks` only when the first turn starts (`core/src/session/turn.rs:340`). The bootstrap therefore observes the pre-prompt surface for 3 s but does not require the event there; each arm's first frozen prompt waits for `SessionStart` with `require_session_start_on_first_turn()`. Do not "fix" this back into a pre-prompt gate: a TUI at an idle composer never emits the event at this version.

**Trust surface (live-verified 2026-10-20).** With hooks present and neither bypass nor pre-trust, 0.163.0 paints a blocking selection modal: `Hooks need review`, `N hooks are new or changed.`, rows `1. Review hooks`, `2. Trust all and continue`, `3. Continue without trusting (hooks won't run)`, footer `enter confirm · esc skip`. The `›` marker starts on row 1 (`Review hooks`). `interactive_trust_all()` therefore reads the marker after each key: `Down` moves it to row 2, then `Enter` confirms. Choosing row 1 opens the Hooks browser (secondary surface, `t trust all`). A changed command with a stale `trusted_hash` produces the same modal with `1 hook is new or changed.`.

**Trust write location (live-verified 2026-10-20).** Codex's interactive trust-all writes `[hooks.state]` into the **active profile file** (for example `openlux-auto.config.toml`), not `config.toml`. The user-layer `config.toml` write used by T1 is also honored. Prefer `config.toml` for production pre-trust, because a launcher refresh of the profile clobbers the profile-layer entries.

**Compaction timing (live-verified 2026-10-20).** `/compact` emits `PreCompact` immediately (45 ms after Enter) and `PostCompact` when compaction finishes (11.6 s in s4), both with `trigger: "manual"` and a **dedicated compaction turn_id** distinct from the surrounding turns. `SessionStart(source="compact")` is queued during compaction but dispatched at the next turn start, so `run_s4` waits for it after submitting the post-compact prompt, not before.

**Mid-turn input is a steer (live-verified 2026-10-20).** A prompt submitted while a turn is busy produces `UserPromptSubmit` during generation (before the first `Stop`) with the **same turn_id**, and the turn completes once. There is no queued second turn and no second `Stop` in TUI mode at 0.163.0. `run_s6` now waits only 15 s for a possible second Stop and records the prompt/Stop turn_id lists.

**Model-request events (live-verified 2026-10-20).** `PreModelRequest` and `PostModelRequest` are declared and have a generated schema (`model-request.command.input.schema.json`) but were not dispatched in any TUI capture, including tool-using and compaction turns. They are outside the 12-event review set at 0.163.0. Treat them as unavailable in TUI mode until a `codex exec` arm proves otherwise.

## Artifact layout per run

```text
tmp/codex-hook-capture/<scenario>/run-<UTCts>/
  launch.json                      # versions, flags, ports, paths, UTC/monotonic pairs
  launch-wrapper-gen<N>.sh         # mode 0600; exports CODEX_HOME and HOUMAO_HOOK_*, execs the selected launcher
  hooks-state.toml                 # T1 only: emitted [hooks.state] blocks (also appended to config.toml)
  hooks.json.pre-perturbation      # T1 only: hooks.json before the SessionStart command change
  hooks.json.perturbed             # T1 only: hooks.json after the change (same path, stale trusted_hash)
  driver-input-events.ndjson       # every driver action, ts_utc + monotonic
  raw-provider-payloads.ndjson     # pristine provider payloads in receive order (payload catalog input)
  run-summary.json                 # event counts/ordering, notes, abort status, permission timings
  codex-home/
    config.toml                    # [projects."<workdir>"] trust_level = "trusted"; [notice]
    hooks.json                     # 14 events, one sync command handler each (absent for T2)
    <lane>.config.toml             # secret-free profile template, mode 0600 (openlux-auto or gac)
  workdir/                         # git-less scratch cwd (s4 gets a small README.md)
  collector/
    events.ndjson                  # one envelope per event (sequence, received_at_utc ms,
                                   #   received_at_monotonic, channel_generation, via, delivery, provider_event)
    collector.json                 # heartbeat/health: status, pid, port, counts, last heartbeat UTC/monotonic
    collector.json.gen<N>          # archived status per collector generation
    collector-gen<N>.log           # collector stderr (event/size/seq/outcome lines)
    emitter.log                    # emitter stderr (bounded ~1 MiB)
    .emitter-seq                   # cross-process client sequence counter
  pane-recording/                  # 5 fps recorder run (s7: pane-recording-resume/ too; T1: pane-recording-perturbed/)
  labels/labels-template.json      # predeclared expectation + empty timestamped slots
  notes/                           # visible-pane snapshots (bootstrap, trust, permission, resume, t1-perturbation)
```

HTTP envelopes carry integer `sequence`; file-fallback envelopes written by `emit_hook.py` carry `"sequence": null` and `"via": "command_fallback"`, so consumers must tolerate a null sequence. The collector resumes `sequence` from the existing `events.ndjson` on restart, so S7's second generation continues the run sequence. `collector.json` counts cover only collector-accepted events for the current generation.

## Collector and emitter design

- **Ack-before-disk.** The HTTP handler validates the bearer token, payload size, and JSON, enqueues `(payload, delivery metadata, receive stamps)`, and returns 204. One writer thread assigns the per-run monotonic `sequence` and appends to `events.ndjson`. This is the same choice the Claude lane made; a collector crash can lose an already-acked event, which the campaign accepts for low hook latency.
- **Millisecond UTC.** `received_at_utc` uses `timespec="milliseconds"`, fixing the Claude lane's named 1-second-granularity leftover. Per-event `received_at_monotonic` shares the system monotonic clock with the runner and recorder, so pane frames align without a wall-clock conversion.
- **Heartbeat file.** `collector.json` is written on start, after every accepted event, on a fixed interval (default 2 s), and on shutdown. `last_heartbeat_monotonic` lets a watcher detect collector death; the file is secret-free.
- **Pristine payloads.** Unlike the Claude lane, the emitter does not inject stamps into the provider payload. Event name and client sequence travel as `?event=<name>&seq=<n>` and `X-Hook-Event` / `X-Hook-Seq` headers, and the collector records them under `delivery`. This keeps `provider_event` faithful for the payload catalog.
- **Emitter contract.** Read stdin to EOF, POST with a 1.5 s timeout (below the 2 s SessionEnd handler budget), append to the run's `events.ndjson` on any failure, print nothing to stdout, always exit 0, and send stderr to a bounded log.

## Observer hooks shape

- All 14 events are subscribed: `PreModelRequest`, `PostModelRequest`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, `Interrupt`.
- Each event has one `{"type": "command"}` handler, `async: false`, timeout 5 s; `SessionEnd` uses 2 s inside Codex's 1-3 s clamp.
- Matchers are omitted everywhere. An absent matcher matches all occurrences; Codex also drops matcher values on events that do not support them when hashing, so omission keeps T1 identity simple.
- The command is `<pixi python> <abs emit_hook.py>`, POSIX shell-quoted. Codex executes it via `<shell> -c`.
- `config.toml` pre-trusts the absolute workload directory (`[projects."<workdir>"] trust_level = "trusted"`) because Codex 0.162+ shows a workspace-trust screen under bypass in untrusted git-less workdirs. It also sets `[notice] hide_full_access_warning = true`. Approval policy and sandbox mode are left to launch flags.

## Trust hash (`hash_hook.py`)

The algorithm mirrors `extern/orphan/codex` at the campaign baseline:

- Identity: `{event_name, [matcher], hooks: [normalized_handler]}`.
- `event_name` is the snake_case label from `hooks/src/lib.rs::hook_event_key_label`.
- Matchers are kept only for `PreToolUse`, `PermissionRequest`, `PostToolUse`, `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact`; they are dropped for `PreModelRequest`, `PostModelRequest`, `UserPromptSubmit`, `Stop`, `Interrupt`.
- Handler normalization: timeout defaults to 600 s (SessionEnd/Interrupt default 1 s and clamp to 1-3 s); `async` defaults false; `commandWindows` is cleared; `statusMessage` is kept when set; `additionalContextLimit` is kept only for PreToolUse/PostToolUse/SessionStart/UserPromptSubmit/SubagentStart and only when it differs from the 2500-token default. None-valued fields are omitted, matching TOML serialization.
- Serialization: compact JSON (`separators=(",", ":")`) with all object keys sorted recursively, SHA-256, prefix `sha256:`.
- State key: `<absolute hooks.json path>:<event_label>:<group_index>:<handler_index>`, written as `[hooks.state."<key>"] trusted_hash = "sha256:..."`.

```bash
# One handler: prints key and hash.
pixi run python scripts/explore/codex-hook-observation/hash_hook.py \
  --hooks-json <CODEX_HOME>/hooks.json --event PreToolUse --group 0 --handler 0

# Every handler: prints the full [hooks.state...] TOML block (append to config.toml).
pixi run python scripts/explore/codex-hook-observation/hash_hook.py \
  --hooks-json <CODEX_HOME>/hooks.json --emit-state
```

Validation status: the canonicalizer reproduces two declaration hashes hard-coded in Codex's own test suite (`core/tests/suite/hooks.rs`: `sha256:c9ee1aca…` for plugin PreToolUse and `sha256:9eef43ad…` for plugin PostToolUse) and the serializer fixture in `config/src/fingerprint_tests.rs` (`sha256:a5e4c8fb…`). Live validation against the installed 0.163.0 binary's reported `currentHash` is deliberately deferred to campaign arms T1/S2 and is not claimed here. The implementation covers command handlers on Linux/macOS; `mcp_tool`, invalid-matcher skipping, and Windows command selection are not modeled.

## Scratch home and credential lane

`run_capture.py` creates `codex-home/` before launch (Codex requires `CODEX_HOME` to exist), pre-writes the secret-free profile for the selected lane (`openlux-auto.config.toml` or `gac.config.toml`), exports `CODEX_HOME` in the wrapper, and execs the selected launcher with `--refresh-profile` on the first generation only. The launcher then rewrites the same profile, exports the provider key itself, and execs `codex --profile <lane> --dangerously-bypass-approvals-and-sandbox "$@"`. Extra args pass through, so `--dangerously-bypass-hook-trust`, `-c`, and `resume <id>` reach Codex. The live-verified default is OpenLux; the GAC lane is retained for comparison.

Credential hygiene: the provider API key is never read, printed, copied, or embedded by the harness. Only the per-run random bearer token appears in artifacts, inside the mode-0600 wrapper; `collector.json` and `launch.json` are token-free. Raw `events.ndjson` may contain prompt text and tool payloads; treat run roots as sensitive campaign evidence.

## Permission lane limitation (S3)

Both `codex-openlux-auto` and `codex-gac` hardcode `--dangerously-bypass-approvals-and-sandbox`. Codex applies that flag as a harness override, which wins over `-c approval_policy=...`; therefore `PermissionRequest` cannot fire through either default lane. Build a permission launcher by copying the lane launcher with the flag removed (do not print the launcher's key line):

```bash
mkdir -p tmp/codex-hook-capture/launchers
sed 's/ --dangerously-bypass-approvals-and-sandbox//g' ~/.local/bin/codex-openlux-auto \
  > tmp/codex-hook-capture/launchers/codex-openlux-permission
chmod +x tmp/codex-hook-capture/launchers/codex-openlux-permission
grep -c dangerously tmp/codex-hook-capture/launchers/codex-openlux-permission  # expect 0
bash -n tmp/codex-hook-capture/launchers/codex-openlux-permission
```

Run S3 with the absolute launcher path, `--allow-permission-lane`, and the scenario's `approval_policy="on-request"` + `sandbox_mode="read-only"` overrides. Read-only is required because workspace-write always includes `/tmp`, so the frozen `/tmp` writes would not prompt. The live modal offers `Yes, proceed (y)`, `Yes, and don't ask again ... (p)`, and `No, and tell Codex what to do differently (esc)`; there is no `No, continue without running it` option, so `d` is unbound and Escape is the deny key. On allow, `PostToolUse` follows with the same `tool_use_id`; on deny, `Interrupt` follows and there is no `PostToolUse` or `Stop`. Note that `PreToolUse` precedes `PermissionRequest` (source: tool registry runs pre-tool hooks before the approval path), and `PermissionRequest` has no `tool_use_id`.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `HOUMAO_HOOK_COLLECTOR_URL` | Collector endpoint exported by the wrapper (for example `http://127.0.0.1:<port>/v1/hook`) |
| `HOUMAO_HOOK_TOKEN` | Per-run bearer token exported by the wrapper; never embedded in hooks.json |
| `HOUMAO_HOOK_STORE` | Run artifact directory for the fallback `events.ndjson` and `.emitter-seq` |
| `HOUMAO_HOOK_GENERATION` | Collector generation stamped into fallback envelopes |

Each emitter variable has a matching CLI flag for manual runs. The collector itself takes `--store`, `--token`, `--generation`, `--port` (0 picks an ephemeral loopback port), and `--heartbeat-seconds`.

## Replay reducer (E3/E4)

`replay_reduce.py` replays the captured streams into merged posture timelines and checks them against the filled labels. It is stdlib-only, deterministic from the stream's own `received_at_monotonic`, and does not import the production reducer.

```bash
# Synthetic reducer checks (normal, blocked-allow, blocked-deny, compaction, terminal gap, steer).
pixi run python scripts/explore/codex-hook-observation/replay_reduce.py --self-test

# Replay the iteration-1 matrix; print summaries and label checks.
pixi run python scripts/explore/codex-hook-observation/replay_reduce.py --all

# One run with a full per-event timeline.
pixi run python scripts/explore/codex-hook-observation/replay_reduce.py \
  --run-root tmp/codex-hook-capture/s3/run-20261020T043111Z --timeline
```

The reducer uses `turn_id` epochs, pairs `PermissionRequest` back to the preceding `PreToolUse`, settles allow on the same-`tool_use_id` `PostToolUse`, settles deny on `Interrupt`, holds posture through `PreCompact`/`PostCompact`, leaves `work=unknown` because Codex `Stop` has no `background_tasks`, and applies the terminal-gap fallback at stream end (`terminal_gap`) or `SessionEnd` with an open turn (`session_end_with_open_turn`).

## Known limitations and deferred checks

- No live Codex session is started by the build or by G0; the startup/trust markers were first exercised live on 2026-10-20 (S0/T1/T2/S2 on OpenLux) and are now recorded in the campaign evidence.
- The collector uses ack-before-disk, so a crash between the 204 response and the writer append loses that event. This is an accepted latency trade, documented above.
- The collector accepts only `Content-Length` POSTs and caps payloads at 1 MiB; chunked and oversized requests are rejected (413 for oversized).
- Matchers are not exercised; the harness subscribes with match-all groups.
- `SessionEnd` uses 2 s inside Codex's 1-3 s clamp rather than the 3 s maximum, leaving shutdown headroom.
- Codex clamps `Interrupt` timeouts to 3 s; `hooks.json` declares 5 s, and `hash_hook.py` hashes the clamped value 3 s. The clamping warning is expected.
- S2's `--interactive-trust` path was live-exercised on 2026-10-20: the marker moved `Review hooks` -> `Trust all and continue` with `Down`, `Enter` confirmed, and Codex wrote 12 `[hooks.state]` entries whose hashes matched `hash_hook.py` exactly (12/12).
- T1's perturbation relaunch was live-exercised on 2026-10-20: changing only the `SessionStart` command in place painted the `1 hook is new or changed.` modal and no event ran; no keypress was sent.
- The GAC lane is dead on this host (HTTP 402 "No active subscription", 2026-10-20). The campaign switched to `codex-openlux-auto`; the OpenLux S0 run completed a full OK turn.
- `PreModelRequest`/`PostModelRequest` never fired in the 2026-10-20 TUI captures (S1, S4, S5, S6, S7, F1); the schema exists but the installed binary does not dispatch them in TUI mode.
- S6's predeclared "second turn after queued input" is not what 0.163.0 does: the second prompt steers the running turn (same turn_id, one Stop). The runner now records this instead of waiting 240 s for a nonexistent Stop.
- F1's pane recording ends with a pane-resolution failure (the tmux pane vanished on SIGKILL); this is the expected terminal-gap signature, not a recorder bug.
- S3 was live-exercised on 2026-10-20 with the permission launcher and read-only sandbox: the modal options, `y`/Escape keys, `PermissionRequest` shape (no `tool_use_id`, `tool_input.description`), `PreToolUse`-before-`PermissionRequest` ordering, `PostToolUse` on allow, and `Interrupt` on deny are all recorded in the S3 evidence doc.
- S3 requires a custom launcher as described above.
- `replay_reduce.py` keeps `work=unknown` for Codex because `Stop` has no `background_tasks`; label checks allow a 3 s terminal lookahead (hook terminals can land after the visible frame) and report pre-channel or TUI-only trust labels as n/a.
- The pane pid is the Node shim that spawns the native Codex binary; F1 kills the whole descendant tree because killing the shim alone can orphan the native process.
- File-fallback ordering uses `emitter_seq`, a run-local flock counter; HTTP ordering uses the collector's authoritative `sequence`.
