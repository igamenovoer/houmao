## Context

The interactive CAO demo already provides a stateful `start` / `send-turn` / `inspect` / `stop` lifecycle, but its startup path still assumes a friendlier local environment than real developers actually have. In practice, the default shell wrapper can produce an incompatible pair of launcher home and repo workdir, a healthy loopback `cao-server` can be reused even when it was started with a stale CAO `HOME`, the helper scripts do not share a consistent confirmation flag surface, and stale `AGENTSYS-alice` tmux state can outlive the demo's persisted state file.

This change is explicitly about operator experience. The tutorial workflow should be runnable from a normal shell without requiring developers to first reason about CAO home-policy internals, manually stop an old local `cao-server`, manually create a safe CAO home, or clean up stale tmux sessions.

## Goals / Non-Goals

**Goals:**
- Make the default interactive demo startup path work from any caller `pwd` as long as the user is invoking the scripts from this repository checkout.
- Make omitted defaults repository-root-derived for this demo pack without broadening shared runtime-wide default behavior.
- Ensure the default startup path provisions a per-run trusted home and git worktree so CAO workdir validation accepts the demo run without extra environment overrides.
- Make `start` self-healing for stale loopback `cao-server` state and stale canonical demo session identity.
- Require explicit confirmation before replacing an existing verified local `cao-server`, with a consistent `-y` escape hatch across all demo scripts.
- Preserve explicit overrides for workspace and launcher-home inputs when an operator intentionally customizes them.

**Non-Goals:**
- Changing shared launcher behavior or introducing a reusable launcher-level replace/recycle feature.
- Turning the interactive demo into a general-purpose CAO process manager for arbitrary ports or remote CAO targets.
- Changing the demo's fixed-loopback CAO contract away from `http://127.0.0.1:9889`.
- Changing shared `brain_launch_runtime` default-path behavior outside this demo pack.
- Redesigning turn parsing or verification semantics beyond the startup robustness needed to make the demo reliably launchable.

## Decisions

1. Keep repository-derived defaults scoped to the interactive demo pack.
Rationale: the wrapper flow is supposed to be runnable from any shell location, and the interactive demo module should honor the same omitted-default contract, but the change is not intended to alter shared `brain_launch_runtime` defaults or launcher-wide path resolution.
Alternatives considered:
- Fix only `run_demo.sh` and leave the Python demo CLI cwd-sensitive: better than today, but still leaves the demo's lower-level entrypoint inconsistent with the wrapper contract.
- Broaden shared runtime defaults: rejected because the change only hardens this tutorial surface.

2. Provision a per-run trusted home and nested git worktree by default.
Rationale: the current default failure came from a trusted-home/workdir mismatch. Using `<repo-root>/tmp/demo/cao-interactive-full-pipeline-demo/<ts>/` as the per-run root and `<run-root>/wktree` as the worktree keeps CAO state scoped to the run while guaranteeing that the effective workdir remains inside the trusted home.
Alternatives considered:
- Keep launcher home under a reusable workspace directory: rejected because the default workdir can still fall outside the trusted home.
- Default launcher home to the repo root or its parent: workable, but less isolated than a per-run run root and more likely to leave CAO state in shared locations.

3. Require explicit confirmation before replacing an existing verified local `cao-server`.
Rationale: the demo should prefer deterministic startup over silently inheriting stale server state, but replacing a developer's existing verified local CAO server is destructive enough that it should be opt-in by default. A shared `-y` contract keeps automation and future extensions consistent.
Alternatives considered:
- Always trust an already-healthy server: this is the current failure mode.
- Always replace a verified server without prompting: easy for reruns, but too destructive as the default tutorial experience.
- Kill any process on the fixed port: rejected for safety.

4. Keep fixed-port recycle semantics in the demo layer.
Rationale: the interactive demo already owns startup orchestration around launcher `status` / `start` / `stop`, so the new replacement prompt and cleanup behavior can live there without widening the shared launcher contract.
Alternatives considered:
- Add launcher-level replace/recycle semantics: reusable, but out of scope for a change that only targets one tutorial pack.

5. Treat replacement startup as a clean-slate reset.
Rationale: the canonical tutorial identity `AGENTSYS-alice` is stable across runs, and stale turn/report artifacts can also contaminate the next run. The safest mental model is "start new": kill what is left from the previous run, clean the leftovers that should not survive, then launch the new session.
Alternatives considered:
- Only stop the previously recorded active state: misses stale tmux sessions created by partial or failed earlier runs.
- Runtime-only cleanup with no local artifact reset: still leaves previous-run artifacts bleeding into the next verification flow.

## Startup Model

1. Resolve `repo_root` from the checked-out repository and derive omitted demo defaults from it. This applies to the interactive demo wrapper scripts and `gig_agents.demo.cao_interactive_full_pipeline_demo`, but not to shared runtime-wide defaults outside this demo.
2. When the operator does not supply custom workspace/home/workdir values, allocate a per-run root at `<repo-root>/tmp/demo/cao-interactive-full-pipeline-demo/<ts>/`, create a git worktree at `<run-root>/wktree`, and treat `<run-root>` as the default CAO trusted home. Demo-local runtime/log/report/state artifacts live under the per-run root.
3. Before launch, perform a clean-slate reset for the canonical tutorial identity: try to stop any existing `AGENTSYS-alice` session, kill leftover tmux state if needed, and clear prior-run demo artifacts that should not survive into the next run.
4. Check the fixed local CAO target `http://127.0.0.1:9889`. If a verified `cao-server` is already serving the port, prompt before replacing it unless `-y` was supplied. If the operator declines, exit without creating an active state artifact. If the port occupant cannot be safely verified as `cao-server`, fail explicitly and leave no active interactive state behind.
5. Start the replacement local CAO server context using the existing launcher status/start/stop primitives from the demo module, then launch the new interactive session and persist the new active state.

## CLI Contract

- `run_demo.sh`, `launch_alice.sh`, `send_prompt.sh`, and `stop_demo.sh` all accept `-y` as a demo-wide yes-to-all flag.
- Commands that do not prompt today still accept `-y` without error so future prompt-bearing extensions do not need one-off wrapper semantics.
- Help text and documentation should explain the per-run worktree/trusted-home layout and that `-y` bypasses confirmation prompts such as CAO server replacement.

## Risks / Trade-offs

- [Risk] Replacing a verified local `cao-server` on `127.0.0.1:9889` can interrupt other CAO work on the same machine. -> Mitigation: prompt before replacement by default, keep `-y` explicit, and leave non-CAO occupants as safe failures.
- [Risk] Per-run git worktrees increase disk usage and startup work. -> Mitigation: scope them under `tmp/demo/cao-interactive-full-pipeline-demo/` so they are easy to inspect and clean, and optimize for tutorial reliability over minimal filesystem churn.
- [Risk] Clean-slate startup can remove stale `AGENTSYS-alice` state or previous-run artifacts that a user wanted to inspect. -> Mitigation: keep the behavior scoped to the documented tutorial identity and per-run demo directories, and make `start` explicitly own the semantics of replacing the previous run.
- [Trade-off] Startup will become slightly slower because it may create a worktree, reset local artifacts, and stop/restart local services before launching the session. -> Mitigation: optimize for reliability first; this is a manual tutorial surface, not a latency-sensitive production path.

## Migration Plan

1. Update the demo wrapper scripts and README-facing parameter descriptions so the default path model uses a per-run demo root/worktree layout and every wrapper accepts `-y`.
2. Refactor the Python demo module to resolve omitted defaults from `repo_root`, provision the default per-run worktree/home layout, and preserve explicit overrides.
3. Add demo-local startup preflight logic for clean-slate `AGENTSYS-alice` reset and prompt-confirmed fixed-port CAO server replacement using existing launcher primitives.
4. Extend unit and integration coverage for the new default layout, `-y` contract, cleanup behavior, and startup recovery paths.
5. If issues arise, rollback is limited to reverting the interactive demo pack and its tests; no external data migration is required.

## Open Questions

- No major open questions remain for the artifact phase. The desired behavior is intentionally opinionated: this tutorial startup should favor a known-good per-run demo environment over preserving stale local CAO, tmux, or prior-run artifact state.
