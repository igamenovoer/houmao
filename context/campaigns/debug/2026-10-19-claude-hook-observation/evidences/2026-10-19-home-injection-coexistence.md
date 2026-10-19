# Evidence: Home-injection coexistence arm (claude 2.1.303, DeepSeek relay, deepseek-flash[1m])

Date: 2026-10-19 (iteration-1 addendum). Arm: design 2.2's managed-home fallback exercised as a primary path. Question: do the 9 observer hooks fire when injected into a managed home's `settings.json` via `CLAUDE_CONFIG_DIR`, and do they coexist with operator-authored hooks in the same file? Verdicts feed the KQ-1 P1.4 reframe and the Part B design correction.

## Run Identity

| Component | Value |
| --- | --- |
| Run root | `tmp/hook-capture/s1/run-20261019T144731Z/` (tmux `hookcap-s1-2008856`, 21 pane samples 14:47:31–14:47:36) |
| Injection | `--inject-via home` (new harness mode): wrapper exports `CLAUDE_CONFIG_DIR=<run-root>/claude-home`, passes **no `--settings`** (grep-verified: the string `--settings` does not appear in `launch-wrapper-gen1.sh`) |
| Scratch home seeding | Mimics `claude_bootstrap.py`: `settings.json` with `skipDangerousModePermissionPrompt: true` plus hooks; `.claude.json` with `hasCompletedOnboarding: true, numStartups: 1`. Settings SHA-256 `7d33d4fe…` (preserved intact in the run root) |
| Merged hooks | Observer block (same 9-event shape as the `--settings` arm) plus a dummy operator `UserPromptSubmit` command hook (`bash operator_hook.sh`, stdin discarded, stdout silent, exit 0) that appends to `operator-hook-marker.txt`. Operator group first, observer group second |
| Collector | gen 1, started 14:47:31 UTC / monotonic 3476002.294363; 5 accepted, 0 rejects of any kind |
| Model verification | banner `deepseek-flash[1m]` (gate passed) |
| Labels | 3 ranges filled (`s1-turn-1` s000006–s000013, `s1-turn-2` s000014–s000018, `s1-exit` s000019–s000021) |

## Ordered Event Sequence

| Seq | Event | received_at_utc | Notes |
| --- | --- | --- | --- |
| 1 | `SessionStart` | 14:47:32 | from the home settings layer; `via: http` (emitter POST); within 1 s of launch (14:47:31) |
| 2 | `UserPromptSubmit` | 14:47:32 | frozen prompt 1; both the operator command hook and the observer HTTP hook were configured for this event |
| 3 | `Stop` | 14:47:34 | `last_assistant_message: OK` |
| 4 | `UserPromptSubmit` | 14:47:34 | frozen prompt 2 |
| 5 | `Stop` | 14:47:35 | `last_assistant_message: 4` |

## Verdicts

| # | Check | Result |
| --- | --- | --- |
| 1 | `SessionStart` within 15 s from the home layer | **Pass**: < 1 s |
| 2 | Every family S1 exercises arrives (UPS x2, Stop x2) with payload parity vs the `--settings` S1 run | **Pass**: field inventory byte-identical for all three families (verified programmatically against `s1/run-20261019T131758Z`) |
| 3 | `$HOUMAO_HOOK_TOKEN` interpolation works from the home layer | **Pass**: zero unauthorized rejects; all 5 events accepted |
| 4 | Operator hook undisturbed (marker file has 2 lines) | **Pass**: `operator-hook-marker.txt` has exactly 2 lines (SHA-256 `175644e5…`); the merge preserved the operator entry and both hooks fired per prompt |
| 5 | No `--settings` passed; flag slot provably free | **Pass**: wrapper contains no `--settings`; `launch.json` records `inject_via: home`, `observer_settings: null` |

## Trust Dialog Observation (data point)

The workspace-trust dialog **appeared** on the fresh scratch home (frame s000001, 14:47:31: `Quick safety check`, options `No, exit` / `Yes, I trust this folder`), was accepted (Down, Enter), and logged. This is the first session in the campaign to show it: every prior run reused the host home where trust state already existed. Conclusion: seeding `.claude.json` with `hasCompletedOnboarding`/`numStartups` alone does **not** suppress the trust dialog; the managed-home bootstrap's project-trust keys (`projects.<workdir>.hasTrustDialogAccepted`, seeded by the `claude.ensure_project_trust` provider hook per `registry/claude.yaml`) are load-bearing for unattended fresh-home starts, exactly as that registry's evidence note says.

## Managed-Launch Args Surface (for the P1.4 reframe)

Verified by reading `src/houmao/agents/launch_policy/` and `src/houmao/agents/realm_controller/launch_plan.py` (read-only):

- Managed realm_controller launch plans build their arg lists from the resolved launch behavior plus policy and provider-generated args; there is no operator-controlled extra-args passthrough in the managed claude launch path (`extra_args` exists only on the codex headless backends).
- The raw operator-facing launch-helper CLI (`launch_policy/cli.py`) does append a `--` passthrough (`command = [result.executable, *result.args, *passthrough]`), and the claude policy's `validate.reject_conflicting_launch_args` currently owns only `--dangerously-skip-permissions`; `--settings` is not an owned arg. A conflicting `--settings` via that raw helper would reach the provider unvalidated today. With home-primary injection the managed path no longer needs `--settings` at all, so the practical conflict degenerates; hardening the raw helper (own or disallow `--settings`) remains a named follow-up.

## Gate Verdicts

| Gate | Verdict |
| --- | --- |
| G2 (home scope) | **Pass**: all exercised families fired from the home layer |
| G3 (pairing) | **Pass**: 21 samples + 5-event stream + 3 labels + monotonic/UTC pair |

## Cleanup

tmux killed by teardown; collector SIGTERMed; no leftovers. No `src/` or `tests/` changes; credential hygiene unchanged.
