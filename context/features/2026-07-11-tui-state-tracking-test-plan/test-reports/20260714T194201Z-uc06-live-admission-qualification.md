# UC-06 Live Admission Qualification

## Result

The real `houmao-mgr agents single ... gateway prompt` path passed the UC-06 admission-policy matrix for Claude Code, Codex CLI, and Kimi Code. Each provider demonstrated ready-only success from ready/no-pending, ready-only `not_ready` refusal while busy/no-pending, two successful pre-repaint `if-no-pending` calls, later `pending_input` refusal after the tracker observed `yes`, and successful `always` dispatch while pending.

Claude and Kimi naturally consumed pending input and returned to stable ready/no-pending. Codex's upstream model request timed out after WebSocket-to-HTTPS fallback despite the required proxy posture. Its admission decisions still passed. Two explicit gateway interrupts then produced an observed `yes → no` pending transition and stable ready return. The Codex provider-completion lane is tainted by that external timeout; the gateway-policy lane passes.

No provider displayed a permission or login confirmation in unattended mode. Gemini was not launched or tested.

## Launch and Recording Provenance

All raw TUIs were launched through the `houmao-dev-launch-agents` development workflow, then adopted with `houmao-mgr agents self join`, attached to background gateways, and recorded before any test prompt. Each provider used an isolated copy of `tests/fixtures/test-projects/boltons` under `tmp/houmao-dev-testing/20260714T191756Z-uc06-live/`.

| Provider | Version | Launcher and credential route | Unattended posture | Tmux session and pane | Recording |
|---|---|---|---|---|---|
| Claude Code | 2.1.209 | First-priority `claude-kimi` wrapper | wrapper-owned bypass | `HMUC06-claude-191756`, `%198` | `claude/capture/recording` |
| Codex CLI | 0.144.3 | Native `codex`; `codex login status` passed | `--dangerously-bypass-approvals-and-sandbox` | `HMUC06-codex-191756`, `%199` | `codex/capture/recording-codex-a002` |
| Kimi Code | 0.24.1 | Native configured-provider auto credential | `--auto` | `HMUC06-kimi-191756`, `%200` | `kimi/capture/recording-kimi-a001` |

Codex inherited the existing `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, `NO_PROXY`, and lowercase equivalents. The configured HTTP, HTTPS, and all-proxy variables used port 7990. No product code, generic skill, or launch command introduced or overrode that port. Values and credential material are excluded from artifacts and this report.

The recorder requested a 0.05-second interval for every provider. Capture overhead yielded about 7,700 samples per full session. The first Codex recorder start collided with Claude's recorder because both attempted the basename-derived session `HMREC-recording`; that partial attempt remains at `codex/capture/recording`. The successful Codex recording used the fresh `recording-codex-a002` attempt. Every provider agent tmux session has a complete stopped recording.

| Provider | Samples | `pane_snapshots.ndjson` SHA-256 | Session cast SHA-256 | Taint |
|---|---:|---|---|---|
| Claude | 7,800 | `511a83401f9eaa845361fa712798f91a32c51a18f27c090a6a04dc3e3dd4c673` | `5f3eb28f5715dce9507c26eaae4410c75095aec32130d27031477fa492eb449f` | Preserved driver attempts and detector fix described below |
| Codex | 7,684 | `46e02f3c067bc7a4e2d0fa0232808335475e6032c411560a7bf60d26a2038c32` | `218915e30e0acc049340e5b6d6f499bcb1e6087f53fd84491621c39ff45aafd5` | External model timeout; explicit interrupt recovery; partial recorder attempt retained |
| Kimi | 7,678 | `2f56f5867a9539eaf8cf39b346cec752d0146be9b416fea331844e53f8847281` | `6f496e7d33d666ecec966e811fba3d303f4ca829894d0b65677b2654cc376d47` | none |

Launch metadata, the exact task definition, frozen-evidence manifests, driver source, decisions, tracked-state polls, gateway runtime artifacts, recordings, replay output, videos, and manifests remain under `tmp/houmao-dev-testing/20260714T191756Z-uc06-live/`.

## Policy Results

The test gateway observation interval was set to 0.5 seconds to make the documented pre-repaint window repeatable. The two conditional CLI processes started together. This changed only the test attachment configuration.

| Check | Claude | Codex | Kimi |
|---|---|---|---|
| Ready/no-pending `ready-only` | success, `ready_only` | success, `ready_only` | success, `ready_only` |
| Busy/no-pending `ready-only` | `not_ready` | `not_ready` | `not_ready` |
| Pre-repaint conditional call 1 | success, `if_no_pending` | success, `if_no_pending` | success, `if_no_pending` |
| Pre-repaint conditional call 2 | success, `if_no_pending` | success, `if_no_pending` | success, `if_no_pending` |
| Busy/no-pending queue probe | success | Pre-repaint calls created visible pending input | success |
| Conditional call after observed `yes` | `pending_input` | `pending_input` | `pending_input` |
| `always` while observed `yes` | success, `always` | success, `always` | success, `always` |
| Pending consumption | natural | explicit gateway interrupt after external timeout | natural |
| Stable ready/no-pending return | natural | second explicit gateway interrupt | natural |

Gateway `events.jsonl` records the selected policy and the tracked readiness, pending, editing, accepting, turn, and stability facts for every submission or refusal. Relevant event-log hashes are:

- Claude: `41da418260ad1eaa9e69010c206a3e08e0f26cd947e73089aafe9345cac1cafc`
- Codex: `773fbacb4f0b83739a1bd563ce299f2368cc9997573c8bca248dd9d7fdf2f75e`
- Kimi: `5af6f9cbce24780bb5198da69213eac6c23181cdea47527e43b9473f38f4403f`

The two pre-repaint calls reached each gateway before the watched state changed. Both calls succeeded for every provider, confirming that Houmao does not reserve a pending slot. Claude and Kimi rendered the closely spaced text as one combined provider queue item; Codex rendered one combined queued-follow-up block. That provider-native coalescing does not alter the gateway result: later decisions changed only after the tracker observed pending input.

## Claude Live Detector Finding and Fix

Claude attempt 3 exposed one real detector mismatch. Claude Code 2.1.209 rendered this live structure during a shell command:

```text
  ❯ queued preview

──────────────── composer upper rule ────────────────
❯ Press up to edit queued messages
──────────────── composer lower rule ────────────────
```

The UC-05 recording had no blank spacer between the preview and upper rule. The detector stopped at the spacer and returned `no` while the pane visibly contained pending input. The implementation now permits exactly one blank spacer before applying the existing indented-row and semantic-style checks. Two blank lines, intervening assistant/tool cells, and unrecognized styles remain non-positive. The regression test `test_claude_pending_input_allows_one_live_composer_spacer_but_not_two` passes.

After restarting the test gateway with the fixed code, the pending-only continuation observed `pending_input=yes`, rejected `if-no-pending` with `pending_input`, accepted `always`, observed pending consumption during the active turn, and returned to stable ready/no-pending. Replaying all 7,800 Claude recording samples with the fixed 2.1.x profile also recognizes the queued spans used in the aligned video.

## Provider Checkpoints

| Provider | Busy/no-pending | Busy/pending | Consumed | Ready return |
|---|---|---|---|---|
| Claude | `active`, ready `unknown`, pending `no`, unstable | `active`, ready `unknown`, pending `yes`, unstable | `active`, pending `no` | `ready`, ready `yes`, pending `no`, stable |
| Codex | `active`, ready `no`, pending `no`, unstable | `active`, ready `no`, pending `yes`, unstable | transition at `2026-07-14T19:34:20Z`: pending `yes → no` | final transition sequence reached `ready`, ready `yes`, pending `no`, stable |
| Kimi | `active`, ready `no`, pending `no`, unstable | `active`, ready `no`, pending `yes`, unstable | `active`, ready `no`, pending `no` | `ready`, ready `yes`, pending `no`, stable |

The Kimi 0.24.1 run selected the conservative fallback profile because the maintained version-specific profile is 0.23.x. The fallback still classified the recorded queue and lifecycle correctly. This report does not claim that 0.24.x has become a maintained version-specific profile.

## Review Videos

The run-local generic renderer aligns each pane frame with replayed current tracker state, the latest live gateway poll, the latest gateway decision facts, and the latest CLI result. Videos use H.264, `yuv420p`, 1800×1000, and 2 fps. Representative first, pending, and final frames were visually inspected after encoding.

| Provider | Video | Frames / duration | SHA-256 |
|---|---|---:|---|
| Claude | `claude/review/aligned/uc06-aligned-review.mp4` | 1,049 / 524.5 s | `400a6071dd482624a893e4b9f29e7ee5511bff0581766b55a382f3d5a31f85b8` |
| Codex | `codex/review/aligned/uc06-aligned-review.mp4` | 601 / 300.5 s | `3bf5276d0a47e57a7f08ce9ed3da688a1235225914de3d73f4a05e68c7ea6975` |
| Kimi | `kimi/review/aligned/uc06-aligned-review.mp4` | 409 / 204.5 s | `4ffffbabc77920b18fed4f8ff0c40226e5c81e9c04d97dbd30fb14fb6adfdf57` |

Each provider directory contains `review/aligned/video-manifest.json` with input hashes, decision and live-state paths, ffprobe output, representative-frame paths, and the video digest.

One useful frame-level observation is intentional: immediately after pre-repaint submission, a pane/replay frame can already show pending `yes` while the latest live poll and gateway decision still say pending `no`. A later watched snapshot changes admission. This is the exact observational concurrency contract; prompt notes and dispatch history did not synthesize pending input.

## Commands and Artifact Authority

The maintained CLI surface under test was:

```text
houmao-mgr --print-json agents single --agent-name <agent> gateway prompt \
  --admission-policy <ready-only|if-no-pending|always> \
  --prompt <canary>
```

The live run used schema-v2 gateway requests generated by the CLI. Unit and proxy suites separately cover strict rejection of schema version 1, request `force`, removed `--force`, native headless nondefault policies, TUI new-session nondefault policies, structured unknown refusal, and renderer formats.

`pane_snapshots.ndjson` is the visual and replay authority. Gateway `events.jsonl` and driver `gateway-decisions.ndjson` are the admission-decision authority. Driver `tracked-state.ndjson` contains sparse live polls. `state_observed_uc06-review.ndjson` is current offline replay output and is never treated as the source of the live gateway decision.

## Conclusion

UC-06 live gateway admission passes for Claude, Codex, and Kimi. The run confirmed policy forwarding, conservative pending refusal, unconditional dispatch, and the expected pre-repaint race through the real CLI and gateway. Claude's newly observed one-spacer layout is fixed and regression-tested. Codex's model completion remains externally tainted by a request timeout, but its complete policy sequence and tracker recovery are recorded and reviewable.
