# Evidence: T1 pre-trusted hash arm (codex-cli 0.163.0, openlux-auto lane, gpt-6.1-sol)

Date: 2026-10-20. Iteration: [plan 1](../iterations/2026-10-20-plan-1-codex-hook-capture-matrix.md). Arm: T1 (P1.2). Key question: [KQ-1](../key-questions/KQ-1-unattended-trust-injection.md).

## Run Identity

| Component | Value |
| --- | --- |
| Deliverable run | `tmp/codex-hook-capture/t1/run-20261020T040411Z/` (tmux `codexhook-t1-2925906`, pane `%166`) |
| Flawed run 1 (kept as driver record) | `tmp/codex-hook-capture/t1/run-20261020T040030Z/` (tmux `codexhook-t1-2918016`, pane `%162`) |
| Tool | `codex-cli 0.163.0`, native sha256 `8a96f66d…`, via `~/.local/bin/codex-openlux-auto` (lane `openlux-auto`, profile `openlux-auto.config.toml`) |
| Flags | **no** `--dangerously-bypass-hook-trust` (launcher args length 0) |
| Hook config | `codex-home/hooks.json` (14 events, sha256 `5b0c1325…`) plus 14 `[hooks.state."<key>"]` entries pre-written into `codex-home/config.toml` by `hash_hook.py --emit-state` |
| Collector | gen 1 port 41135; gen 2 port 40445 for the perturbation relaunch |
| Recording | main: 64 samples at 0.2 s; perturbed: 6 samples at 0.2 s; both non-empty, not tainted |
| Labels | `t1-session-start`, `t1-turn`, `t1-perturbation` filled with digests |

## Main Half: pre-written hash runs hooks with no bypass

Ordered events (gen 1):

| Seq | Event | received_at_utc | Monotonic | Key fields |
| --- | --- | --- | --- | --- |
| 1 | `SessionStart` | 04:04:18.683 | 3523809.527095 | `session_id`, `source: startup`, `model: gpt-6.1-sol`, `permission_mode: bypassPermissions` |
| 2 | `UserPromptSubmit` | 04:04:18.726 | 3523809.569990 | `turn_id`, `prompt`, `model`, `cwd`, `transcript_path` |
| 3 | `Stop` | 04:04:25.588 | 3523816.432115 | `turn_id`, `last_assistant_message: "OK"`, `stop_hook_active: false` |
| 4 | `SessionEnd` | 04:04:26.128 | 3523816.972330 | `reason: "other"`, no `turn_id` |

- Composer ready 0.68 s after launch with zero keypresses and **no hooks trust modal**.
- Prompt Enter at 04:04:18.674; `SessionStart` 9 ms later; `UserPromptSubmit` 43 ms after that.
- The launch carries no bypass flag in `launch.json` or the wrapper. The only reason the hooks executed is that every pre-written `trusted_hash` matched Codex's current hash.
- Because one mismatched handler would have painted the review screen, the absence of the screen validates the hash implementation across all **12 reviewable** handlers. (`PreModelRequest`/`PostModelRequest` are declared and hashed but are not part of the 0.163.0 review set; S2's Codex write enumerates the same 12.)

## Perturbation Half: stale hash blocks execution

| Field | Value |
| --- | --- |
| Handler | `SessionStart` group 0 handler 0 |
| State key | `<run>/codex-home/hooks.json:session_start:0:0` |
| Trusted hash (unchanged) | `sha256:01b7a1ca44f080665a491390811172cfa69929a5c91871629edd19501f671cb9` |
| Perturbed command | `…/emit_hook.py # t1-perturbation` (shell comment: semantically identical if executed) |
| Perturbed hash | `sha256:d3fa66a17b8ac1a0ba9a74443a104bac8b8a6375d03540f648aaca753fd7e21f` |
| Surface | `Hooks need review / 1 hook is new or changed.` with rows `Review hooks`, `Trust all and continue`, `Continue without trusting (hooks won't run)`; initial marker on `Review hooks`; footer `enter confirm · esc skip` |
| Keypresses | **none** |
| Generation-2 events | none; no `SessionStart` in the perturbed session |

The perturbed launch painted the review screen 0.4 s after the session surface appeared, and the run was torn down at the modal without any input. The changed command (a shell comment that would execute identically) is enough to break trust, so the trust identity is the normalized command hash, not a path/source check.

Pane evidence: `notes/t1-perturbation-surface.txt` (exact modal), `pane-recording-perturbed/pane_snapshots.ndjson` sample `s000002` (modal), labels `t1-perturbation`.

## Flawed Run 1 (driver surface-detection bug)

`run-20261020T040030Z` had a valid main phase but a corrupted perturbation phase:

- The driver sampled the splash before the review modal painted and immediately sent the frozen prompt. The text was swallowed by the modal and the Enter selected `Review hooks`, opening the Hooks browser (`s000002` onward).
- No `SessionStart`/`UserPromptSubmit` occurred in generation 2; `/quit` was ignored until teardown. The browser did show `SessionStart 0/1 !` and `1 hook needs review before it can run`, so the stale-hash detection was real, but the recording does not cleanly show the modal before a keypress.
- Fix: `wait_for_startup_surface()` now requires the composer to stay free of trust markers for 3 s and detects both the selection modal and the Hooks browser. The retry above is the deliverable. This is run 1 of 2 for the arm; the retry is run 2, within the two-attempt limit.

## KQ-1 Verdict

**P1.2 CONFIRMED.** A launch with `[hooks.state."<key>".trusted_hash]` pre-written into the runtime home and **no** bypass flag executes the observer hooks unattended: `SessionStart` arrives at first-turn start, `UserPromptSubmit` follows, and the turn completes with `Stop`. Perturbing only the `SessionStart` command while leaving the hash in place produces the blocking review modal and prevents execution, proving the hash is the load-bearing trust mechanism. Live hash validation is exact (see the S2 evidence doc: 12/12 Codex-written hashes equal `hash_hook.py`).

**Design note for the managed path:** Codex's own interactive trust-all writes `[hooks.state]` into the **active profile file** (`openlux-auto.config.toml`), while the T1 pre-trust in `config.toml` also works. If a launcher refreshes the profile on every launch, trust written there is clobbered; pre-writing into `config.toml` is the stable surface.
