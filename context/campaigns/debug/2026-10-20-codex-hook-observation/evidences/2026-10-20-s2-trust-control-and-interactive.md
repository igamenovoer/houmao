# Evidence: S2 trust control and interactive trust-all (codex-cli 0.163.0, openlux-auto lane)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: S2 (P1.3, and the P1.2 key/hash validation). Key question: [KQ-1](../key-questions/KQ-1-unattended-trust-injection.md).

## Runs

| Component | Control | Interactive |
| --- | --- | --- |
| Run root | `tmp/codex-hook-capture/s2/run-20261020T040447Z/` | `tmp/codex-hook-capture/s2/run-20261020T040510Z/` |
| tmux / pane | `codexhook-s2-2927619` / `%170` | `codexhook-s2-2928356` / `%172` |
| Launcher / lane | `codex-openlux-auto` / `openlux-auto` | same |
| Flags | hooks.json, **no** bypass, **no** pre-trust | same |
| Recording | 5 samples at 0.2 s (modal from s000002) | 113 samples at 0.2 s |
| Outcome | aborted at the modal, zero keypresses, zero hook events | trust-all (Down, Enter), composer, full OK turn, SessionEnd |
| Labels | `s2-trust-surface`; `s2-post-trust-composer` = not reached | `s2-trust-surface`, `s2-trust-all-keys`, `s2-post-trust-composer` |

Commands:

```bash
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s2
pixi run python scripts/explore/codex-hook-observation/run_capture.py --scenario s2 --interactive-trust
```

## Control: the exact failure mode is a blocking TUI review

`hooks.json` present, no bypass flag, no `[hooks.state]`. The TUI paints, and waits on, this screen (verbatim from `notes/s2-trust-modal.txt`):

```text
  Hooks need review
  12 hooks are new or changed.
  Hooks can run outside the sandbox after you trust them.

› 1. Review hooks
  2. Trust all and continue
  3. Continue without trusting (hooks won't run)

  enter confirm · esc skip
```

- The modal appears at recorder sample `s000002` (04:04:48.8, ~0.8 s after launch).
- The runner detected it before any keypress and aborted: `no keypress sent`.
- **Zero hook events** arrived (`events.ndjson` is empty); `SessionStart` is first-turn scoped and no turn began.
- This is the documented unattended failure mode: the session hangs forever at the review screen. There is no silent-skip path in TUI mode for untrusted hooks; the modal blocks startup.

Note: the count is **12**, not 14. `PreModelRequest` and `PostModelRequest` are declared in `hooks.json` and hashed by `hash_hook.py`, but the 0.163.0 review/install set does not include them. The same 12-event set appears in the Codex-written state below.

## Interactive: marker-driven trust-all

First live exercise of `interactive_trust_all()`. Exact driver trace from `driver-input-events.ndjson`:

| Step | Time | Pane marker reading | Key sent |
| --- | --- | --- | --- |
| 0 | 04:05:11.326 | `›` on `1. Review hooks` | `Down` (04:05:11.328) |
| 1 | 04:05:11.932 | `›` on `2. Trust all and continue` | `Enter` (04:05:11.934) |
| confirm | 04:05:12.534 | selection confirmed | - |
| composer | 04:05:13.542 | `› Ask Codex to do anything` | - |

Exactly two keys were sent. The `Down` moved the marker from row 1 to row 2; the helper re-read the pane and only then pressed Enter. After Enter, the modal closed and the composer became ready 1.6 s later.

Post-trust turn (same session):

| Seq | Event | received_at_utc | Key fields |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 04:05:18.777 | `source: startup`, `model: gpt-6.1-sol` |
| 2 | `UserPromptSubmit` | 04:05:18.836 | `turn_id`, `prompt: "Reply with exactly: OK"` |
| 3 | `Stop` | 04:05:34.924 | `last_assistant_message: "OK"` |
| 4 | `SessionEnd` | 04:05:35.720 | `reason: "other"` |

Hooks became active in the same session after the trust write (`s2_session_start_after_trust: true`). The turn took ~16.2 s.

## Hash Validation: Codex-written `hooks.state` vs `hash_hook.py`

Codex wrote the trust entries into the **active profile file**, `codex-home/openlux-auto.config.toml`, not `codex-home/config.toml`:

```text
[hooks.state]

[hooks.state."<abs hooks.json>:pre_tool_use:0:0"]
trusted_hash = "sha256:c9413122a3af9d3f54abaa33429f502fd0cbfff2ba83e124ee150e43c943de64"
...
```

The `config.toml` user layer remained without `[hooks.state]`. Both layers work: T1's pre-trust in `config.toml` was honored, and Codex's own write to the profile file was honored. A launcher that refreshes the profile on every launch would clobber Codex's write, so the production pre-trust should target `config.toml` (or re-apply after refresh).

Comparison (Codex-written value vs `hash_hook.py --emit-state` on the same `hooks.json`):

| Event | Codex `trusted_hash` | Result |
| --- | --- | --- |
| `interrupt` | `sha256:7d2dd0fad718dae5564f65ad317594451cd7cc71830cdf6dbcdb171197a2e5f4` | match |
| `permission_request` | `sha256:8a3a7b666e58232bfd74d9207df99698b98a7b4695270fbc80054378dfc2debc` | match |
| `post_compact` | `sha256:ee76ce11baf2bbc51510f645b1f12a9e7374f12f2237e405f09d03f1258b6b92` | match |
| `post_tool_use` | `sha256:268f3fa456a0fb0173e2cedf6e6097d854911f7fdb913f1d24fbf4632e194d70` | match |
| `pre_compact` | `sha256:46bcfd549dc779d21c605a62a8c24112be06569620e02a226b29317ecdfdd354` | match |
| `pre_tool_use` | `sha256:c9413122a3af9d3f54abaa33429f502fd0cbfff2ba83e124ee150e43c943de64` | match |
| `session_end` | `sha256:23f1b22a7c6143ef2304c2b0dd0fb62a807636265f10f5f5f54e1f42b0f1cc6f` | match |
| `session_start` | `sha256:01b7a1ca44f080665a491390811172cfa69929a5c91871629edd19501f671cb9` | match |
| `stop` | `sha256:d5a4d48fe52ebcfd2ca8016b1313d904e254c5fc41c081c8913a9d7d94a62a8a` | match |
| `subagent_start` | `sha256:33153993686f494171b1262c740dc8f13b1ab4299f0648a3fe381eb7d4c938ea` | match |
| `subagent_stop` | `sha256:ec9feffee4db3164cf7d7e1d8da93faa984865313b32be61062e76b07f81cead` | match |
| `user_prompt_submit` | `sha256:bcc195df0dad850d87fc428b2ef0f128f4f8632985df30d0ce79ba6a8b91bc03` | match |

**Exact agreement: 12/12 entries, 0 mismatches, 0 missing, 0 extra in Codex's set.** The two `hash_hook.py`-only keys are `pre_model_request` and `post_model_request`, which Codex did not write because they are outside the review set. This is the empirical validation of the local hash reimplementation: the canonical JSON, TOML serialization, timeout normalization (`Interrupt` clamped to 3 s), and state-key format all reproduce the binary's values byte for byte.

Raw artifacts: `codex-home/openlux-auto.config.toml` (sha256 `9059ef6e…`), `notes/s2-trust-modal.txt`, `notes/s2-trust-step0.txt`, `notes/s2-trust-step1.txt`, `notes/s2-post-trust-attempt.txt`.

## KQ-1 Verdicts

**P1.3 CONFIRMED.** The no-trust control does not silently skip hooks in TUI mode. It paints a blocking `Hooks need review` selection screen with a default-marked `Review hooks` row and waits for input. An unattended session hangs there; zero hook events are delivered. `esc skip` exists, but no unattended process can press it.

**P1.2 key/hash format VALIDATED.** The interactive `Trust all` writes 12 `[hooks.state."<abs hooks.json>:<event>:0:0"] trusted_hash = "sha256:…"` entries into the active profile file, and all 12 hashes match `hash_hook.py` exactly. Combined with T1's no-bypass unattended run and its perturbation control, the pre-trusted-hash arm is fully live-validated.

**Operational note:** the review surface is the selection modal, not the Hooks browser. Choosing `Review hooks` opens the browser, which shows per-event `Active/Installed` counts and a `t trust all` shortcut; that is a secondary surface and is not needed for the unattended path.

**Snapshot caveat:** `notes/s2-trust-step0.txt` and `notes/s2-trust-step1.txt` are blank because each capture raced a full-screen repaint. The authoritative record for those two steps is `driver-input-events.ndjson` (marker readings `Review hooks` then `Trust all and continue`) plus `notes/s2-trust-modal.txt` (the unmoved modal text).
