# CAO Shadow Parser Troubleshooting

This guide covers runtime-owned CAO shadow parsing for:

- `tool=codex`
- `tool=claude`

For the full developer-oriented design guide, see:

- [TUI Parsing Developer Guide](../developer/tui-parsing/index.md)
- [Runtime Lifecycle And State Transitions](../developer/tui-parsing/runtime-lifecycle.md)
- [Claude Parsing Contract](../developer/tui-parsing/claude.md)
- [Codex Parsing Contract](../developer/tui-parsing/codex.md)
- [TUI Parsing Maintenance Guide](../developer/tui-parsing/maintenance.md)

Gemini remains headless-only in this change. Gemini parser architecture follow-up:
`context/issues/feat-gemini-headless-parser-architecture.md`.

## Quick Signals

When `parsing_mode=shadow_only`, runtime failures are explicit and include an ANSI-stripped tail excerpt.

Common error/anomaly signals:

- `unsupported_output_format`: output no longer matches any supported variant.
- `awaiting_operator`: CLI is waiting for approval/selection/setup (`[y/n]`, trust prompt, option menu, login/setup block).
- `unknown`: output matches a supported parser family but lacks known status evidence.
- `stalled_entered`: runtime promoted continuous `unknown` to `stalled`.
- `stalled_recovered`: runtime recovered from `stalled` back to a known status.
- `baseline_invalidated`: the visible scrollback shrank below the recorded pre-submit baseline offset.
- `unknown_version_floor_used`: detected tool version is newer than known parser presets.

Inspect `done.payload.parser_metadata`:

- `shadow_parser_preset`
- `shadow_parser_version`
- `shadow_output_format`
- `shadow_output_variant`
- `shadow_parser_anomalies`
- `baseline_invalidated`
- `unknown_to_stalled_timeout_seconds`
- `stalled_is_terminal`

Inspect `done.payload.surface_assessment` and `done.payload.dialog_projection` when you need to reason about state vs visible transcript separately.

`shadow_parser_anomalies` entries for stalled lifecycle include:

- `phase`: `readiness` or `completion`
- `elapsed_unknown_seconds` on `stalled_entered`
- `elapsed_stalled_seconds` and `recovered_to` on `stalled_recovered`

## CAO Startup Window Hygiene

The runtime pre-creates a bootstrap tmux window during CAO session startup and then asks CAO to create the real agent terminal window. Startup attempts to select the CAO window and prune the bootstrap window (best-effort).

Quick checks:

- `start-session` prints window-hygiene problems as stderr `warning:` lines and keeps JSON stdout unchanged.
- Success path: `tmux attach -t AGENTSYS-...` lands on the agent terminal, and `tmux list-windows -t AGENTSYS-...` shows only the agent window.
- Warning path: attach may land on the bootstrap shell window and/or a second window may remain (bootstrap pruning skipped/failed). Shadow parsing is unaffected; this is window selection/pruning hygiene only.

See: [Brain Launch Runtime window-hygiene checklist](./brain_launch_runtime.md#manual-verification-checklist-cao-startup-window-hygiene).

## Unknown vs Stalled

- `unknown` is parser-owned and means the output format is recognized, but no safe classification (`idle`, `working`, or `awaiting_operator`) was found.
- `stalled` is runtime-owned and means `unknown` stayed continuous for at least `unknown_to_stalled_timeout_seconds`.
- `input_mode = unknown` by itself keeps the surface non-ready, but does not enter `stalled` while `business_state` remains known.
- `stalled_is_terminal=true`: fail immediately at stalled entry.
- `stalled_is_terminal=false`: keep polling and allow recovery.

Tune via brain manifest:

```yaml
runtime:
  cao:
    shadow:
      unknown_to_stalled_timeout_seconds: 30
      stalled_is_terminal: false
```

## Known Failure Patterns

### 1) CAO rejects workdir outside home

Symptom:

```text
Working directory not allowed ... outside home directory /home/<user>
```

Cause:

- CAO tmux working-directory validation only permits paths under the user home tree.
- Repo-local paths like `/data/.../tmp/...` are rejected.

Fix:

- Use `--workdir "$HOME/tmp/<subdir>"` (or any home-subdirectory path).
- Demo scripts now default to:
  - `DEMO_WORKSPACE_PARENT="${HOME}/tmp"`
  - `DEMO_WORKSPACE_SUBDIR="agent-system-dissect"`

### 2) Codex trust prompt blocks readiness

Symptoms:

- Readiness timeout before prompt submission.
- Or explicit operator-blocked behavior with trust/menu text.

Typical Codex trust prompt variants:

- `Allow Codex to work in this folder? [y/n]`
- `Do you trust the contents of this directory?`
- Menu style:
  - `› 1. Yes, continue`
  - `2. No, quit`

Fixes in runtime/parser:

- Codex operator-blocked detection now supports both trust prompt families and `❯` / `›` / `>` menu markers.
- Runtime bootstrap seeds trust for launch context by writing:

```toml
[projects."/abs/workdir/path"]
trust_level = "trusted"
```

into the generated Codex home `config.toml`.

### 3) Turn completion timeout while visible dialog is present

Symptom:

```text
Timed out waiting for shadow turn completion ... shadow_status=idle
```

Tail excerpt already includes a real assistant answer, for example:

```text
› Give a one-sentence greeting that includes the word "runtime".
• Hello, and welcome to the runtime!
```

Cause:

- The runtime no longer uses parser-owned answer extraction as the completion contract.
- Completion now requires a return to `submit_ready` plus either:
  - observed projected-dialog change after submit, or
  - observed post-submit `working`.
- A visible transcript fragment may exist without yet satisfying that lifecycle rule.

Fixes in runtime/parser:

- Baseline capture anchors readiness/completion monitoring and `baseline_invalidated` diagnostics.
- Runtime terminality is driven by `TurnMonitor`, not parser-owned answer extraction.
- The caller should read `dialog_projection` as projected visible transcript, not as an authoritative prompt answer.

### 4) Stalled terminal mode fails fast

Symptom:

```text
Shadow parser entered stalled state (... stalled_is_terminal=True)
```

Expected diagnostics:

- error includes `phase` (`readiness` or `completion`),
- elapsed unknown/stalled durations,
- parser family and tail excerpt,
- no fallback to `parsing_mode=cao_only`.

### 5) Non-terminal stalled mode recovers

Symptom:

- temporary delay while status is `stalled`,
- turn eventually completes successfully.

Expected diagnostics:

- `shadow_parser_anomalies` contains `stalled_entered` and `stalled_recovered`,
- `stalled_recovered.details.recovered_to` shows the recovery status,
- output mode remains `full` throughout shadow-only execution,
- successful `done` payloads still use neutral `message="prompt completed"` and structured projection/state fields.

### 6) Historical `/model` or slash-command history should not wedge readiness

Symptoms:

- a prior manual `/model` or other slash command is still visible in scrollback,
- but the live prompt has already returned to a blank normal prompt,
- and `send-prompt` or demo `send-turn` still appears to wait forever for readiness.

Expected behavior:

- recovered normal prompts should parse as `ui_context=normal_prompt`,
- `input_mode` should become `freeform`,
- `business_state` should return to `idle`,
- historical slash-command output may remain visible in `dialog_projection` without blocking submission.

Operator note:

- Use runtime `send-keys` for live slash-command/menu navigation or raw `Escape`/arrow-key injection.
- Use `send-prompt` only for ordinary prompt turns that should wait for readiness/completion.

If readiness is still blocked, inspect `surface_assessment` first. The likely remaining causes are:

- the active prompt is still actually in slash-command interaction,
- the tool is waiting on a selection/approval surface,
- or the snapshot no longer matches a supported output variant.

## Preset Overrides

Use overrides only as a short-term mitigation while adding a new preset/fixture.

- Claude override: `AGENTSYS_CAO_CLAUDE_CODE_VERSION=<X.Y.Z>`
- Codex override: `AGENTSYS_CAO_CODEX_VERSION=<X.Y.Z>`

Example:

```bash
AGENTSYS_CAO_CODEX_VERSION=0.98.0 \
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --brain-manifest tmp/agents-runtime/manifests/codex/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend cao_rest \
  --cao-base-url http://localhost:9889 \
  --cao-parsing-mode shadow_only
```

## Debug Workflow For Drift

1. Reproduce under `parsing_mode=shadow_only`.
2. Capture CAO `mode=full` output while the terminal is stuck:

```bash
curl -s "http://localhost:9889/terminals/<terminal-id>/output?mode=full" \
  | jq -r '.output' > tmp/shadow-parser-live.txt
```

3. Confirm whether the tail already contains assistant output.
4. If output exists but status does not complete, inspect `done.payload.parser_metadata` (or error metadata) for:
   - `shadow_output_variant`
   - `baseline_invalidated`
   - `shadow_parser_anomalies`
5. Inspect `done.payload.surface_assessment` and `done.payload.dialog_projection` to distinguish:
   - parser state,
   - projected visible transcript,
   - diagnostics-only raw tail excerpts.
6. Add or refresh fixtures and tests.

## Capture A New Drift Fixture

1. Reproduce under `parsing_mode=shadow_only`.
2. Save raw `mode=full` output for the failing turn:

```bash
curl -s "http://localhost:9889/terminals/<terminal-id>/output?mode=full" \
  | jq -r '.output' > tmp/shadow-parser-drift.txt
```

3. Add a curated fixture:
   - `tests/fixtures/shadow_parser/codex/<name>.txt`
   - `tests/fixtures/shadow_parser/claude/<name>.txt`
4. Add or extend unit tests under:
   - `tests/unit/agents/brain_launch_runtime/test_codex_shadow_parser.py`
   - `tests/unit/agents/brain_launch_runtime/test_claude_code_shadow_parser.py`
5. Run tests:

```bash
pixi run python -m pytest tests/unit/agents/brain_launch_runtime/test_codex_shadow_parser.py tests/unit/agents/brain_launch_runtime/test_claude_code_shadow_parser.py
```

6. If needed, temporarily use `--cao-parsing-mode cao_only` while shipping preset updates.
