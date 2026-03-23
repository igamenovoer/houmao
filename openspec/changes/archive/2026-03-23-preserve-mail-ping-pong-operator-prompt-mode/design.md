## Context

The mail ping-pong gateway demo builds participant brain homes from tracked recipes and then launches managed headless agents from the generated brain manifests. The tracked initiator and responder recipes already declare `launch_policy.operator_prompt_mode: unattended`, and the downstream launch-plan pipeline already knows how to consume that manifest field and apply provider-specific launch policy.

The current demo build path drops that field before calling `build_brain_home`. The resulting manifest therefore falls back to `interactive`, the launch plan records an interactive prompt-mode request, and launch-policy provenance is absent in the live managed-headless manifest. That means the demo is not exercising the intended unattended launch posture before kickoff begins.

The current verification story also stops too early. Pytest coverage catches narrow contract drift, but it does not provide one canonical production-level unattended path that uses the real local `claude` and `codex` executables, preserves useful artifacts, and reveals the next blocker once launch posture is fixed.

## Goals / Non-Goals

**Goals:**
- Preserve the tracked recipe operator prompt mode when the demo pack builds participant brain homes.
- Keep the brain manifest as the source of truth for launch posture so the existing launch-plan pipeline applies unattended policy automatically.
- Expose one canonical automatic hack-through-testing path for the real unattended demo flow.
- Make the automatic path fail fast on missing prerequisites, preserve run artifacts on failure, and emit a machine-detectable case result.
- Add stable demo-owned launch posture evidence so automatic runs do not need to reverse-engineer raw session internals to determine whether unattended mode survived launch.
- Keep tmux as a live diagnostic surface for headless participants so user observers can see rolling console output during active turns.

**Non-Goals:**
- Redesign mailbox skill discovery or mailbox prompt wording in this change.
- Introduce a new headless launch API field just for the demo pack.
- Change the default meaning of omitted operator prompt mode for unrelated callers.
- Generalize the pack-local autotest harness into a repository-wide demo framework.

## Decisions

### Decision: Preserve operator prompt mode at brain-build time

The demo pack should pass `recipe.operator_prompt_mode` into `BuildRequest` when building participant homes.

Rationale:
- the recipe already owns this launch intent
- `build_brain_home` already persists that intent into the runtime brain manifest
- the launch-plan pipeline already reads the manifest field and applies unattended launch policy when present

Alternative considered:
- override launch posture later during `HoumaoHeadlessLaunchRequest`
  Rejected because it duplicates launch intent outside the tracked recipe/manifest contract and bypasses the existing manifest-driven launch-policy path.

### Decision: Define one canonical automatic HTT entrypoint for the real unattended path

This change should introduce one pack-local standalone harness:

```bash
scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/run-case.sh \
  --case unattended-full-run \
  [--demo-output-dir <path>]
```

The harness should dispatch into `autotest/case-unattended-full-run.sh`, which owns one bounded unattended run:

1. preflight
2. clean or stop stale demo-owned state under the selected output root
3. `start`
4. launch-posture inspection
5. `kickoff`
6. `wait`
7. `inspect`
8. `verify`
9. `stop`

Rationale:
- HTT needs one production-level path worth driving end to end
- a standalone harness keeps case selection out of `run_demo.sh`
- `start -> kickoff -> wait -> inspect -> verify -> stop` is the shortest real path that both proves unattended launch posture and reveals the next mailbox or gateway blocker

Alternative considered:
- treat `run_demo.sh auto` as the only automatic surface
  Rejected because it does not own HTT-specific preflight, stale-run cleanup, artifact/result bookkeeping, or case selection.

### Decision: Keep an independent interactive companion under the same pack-local `autotest/`

The implemented automatic case should have an operator-facing interactive companion at `scripts/demo/mail-ping-pong-gateway-demo-pack/autotest/case-unattended-full-run.md`.

That guide should be a true step-by-step procedure for agent-driven execution while the user watches. It should not collapse to "run the automatic script."

Rationale:
- the same canonical path should support both unattended execution and interactive observation
- the automatic script and interactive guide serve different operator needs even when they exercise the same flow

### Decision: Headless tmux sessions should stay watchable even though they are not authoritative

The headless demo path should continue to treat tmux as an auxiliary inspection surface rather than a state-truth source, but operators who attach to a participant tmux session during a live turn should see rolling console output from the underlying CLI execution.

For this change, "rolling console output" means the active pane shows ongoing stdout or stderr progress from the current headless CLI invocation closely enough for a human observer to tell that work is progressing, stalling, or failing. The design does not require one specific provider log format, and it does not require tmux observation to drive any server-side lifecycle state.

Rationale:
- user-observed HTT is much less useful if the pane stays blank or frozen while the run is active
- this keeps tmux aligned with the recent headless-state design: it remains a diagnostic container and attach surface, not a lifecycle authority
- the demo already persists tmux session names, so visible rolling output is the missing half of a usable watch experience

Alternative considered:
- rely only on inspect/report artifacts and ignore live pane visibility
  Rejected because the interactive companion case explicitly depends on user observation while the run is active.

### Decision: Use pack-owned preflight, bounded failure behavior, and deterministic artifact locations

The automatic case should fail before launch work begins when required commands or tracked fixture inputs are missing. At minimum, preflight should check:

- `pixi`
- `git`
- `tmux`
- `claude`
- `codex`
- the tracked parameter file and tracked recipe files
- the tracked credential and config roots needed by those recipes

The default automatic HTT output root should be:

```text
.agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output
```

The caller may override that root with `--demo-output-dir <path>`.

Each phase should return non-zero on failure, and failure should preserve the selected output root plus any case log or result files rather than deleting them.

Rationale:
- HTT should discover the next real blocker quickly instead of hanging or waiting for manual cleanup
- a deterministic default output root makes live artifacts easy to inspect and compare across runs
- allowing an override still keeps the path usable for isolated runs

### Decision: Surface stable launch posture evidence in demo-owned control artifacts

The demo pack should expose a machine-readable per-role launch posture summary in `control/inspect.json` and `control/report.json`.

The summary should include enough stable data for automatic verification without depending on raw tmux observation or ad hoc manifest scraping:

- tracked recipe operator prompt mode
- built brain manifest operator prompt mode
- live launch request operator prompt mode
- whether launch policy was applied

The automatic case should treat a mismatch in any of those values as a failure before or during kickoff.

Rationale:
- HTT needs machine-detectable evidence, not just human-readable terminal output
- the prompt-mode regression crosses build-time and live-launch boundaries, so one artifact should summarize both
- demo-owned inspect/report artifacts are a better long-term contract than case-specific path scraping

Alternative considered:
- have the automatic case read raw session manifests only
  Rejected because that makes the HTT contract depend on lower-level runtime file layout instead of the demo pack's own control artifacts.

### Decision: The interactive HTT path should expose tmux attach hints and rolling-output checks

The pack-local interactive guide and shared helpers should tell the operator how to attach to each participant tmux session and what rolling output to look for before and after kickoff. The automatic case may also capture bounded tmux pane snapshots as preserved diagnostics, but those snapshots are evidence for operators rather than lifecycle truth.

Rationale:
- the change now promises a watchable live surface, so the shipped guide should explain how to use it
- bounded pane snapshots make failures easier to inspect after the fact without turning tmux into the machine-readable pass/fail contract

### Decision: Emit a case result artifact in addition to exit status

The automatic case should write one machine-readable result payload under the selected output root, for example:

```text
<output-root>/control/autotest/case-unattended-full-run.result.json
```

The result should include:

- case id
- final status (`passed` or `failed`)
- failure reason when present
- selected output root
- pointers to the key preserved control artifacts

Rationale:
- exit status alone is not enough once operators need to inspect preserved artifacts after a failure
- a result file gives later tools or agents a stable place to look for the summarized outcome

## Risks / Trade-offs

- [Mailbox issues may still remain after this fix] -> Mitigation: the automatic case is intentionally end to end so the next blocker is preserved as evidence instead of being hidden behind ad hoc manual orchestration.
- [Real local tool environments drift more often than pytest fixtures] -> Mitigation: keep pytest coverage for deterministic contract checks, and keep HTT preflight explicit and fail-fast.
- [Adding launch posture to report snapshots changes tracked artifacts] -> Mitigation: keep the added fields concise and stable, sanitize volatile values, and update the expected report snapshot together with the reporting change.
- [The default HTT output root could accumulate stale state] -> Mitigation: the harness should stop or clean stale demo-owned state under that root before starting a new automatic case.

## Migration Plan

1. Update the demo brain-build path to pass through the tracked recipe operator prompt mode.
2. Extend inspect/report generation so per-role launch posture is visible in demo-owned control artifacts.
3. Ensure the launched headless participants keep rolling CLI output visible in their tmux panes during active turns.
4. Add design-phase `testplans/case-unattended-full-run.md` that defines the canonical automatic and interactive variants.
5. Add pack-local `autotest/` assets: harness, automatic case, interactive guide, and shared helpers.
6. Extend deterministic pytest coverage for build-time and artifact-level contract drift.
7. Exercise the automatic case in a real local environment when prerequisites are available, preserving the resulting artifacts.

## Open Questions

- None for this scoped change. If the automatic full run still fails after unattended posture is preserved, the expected follow-up is mailbox skill or mailbox prompt contract work rather than another launch-posture change.
