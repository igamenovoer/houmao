## 1. Repo-Root Default Alignment

- [x] 1.1 Update `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh` and the helper wrappers so default startup provisions the per-run `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/` layout, creates the nested `wktree` workdir, remains runnable from arbitrary caller `pwd`, and accepts `-y` consistently across all demo scripts.
- [x] 1.2 Refactor `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py` so omitted defaults are derived from `repo_root` for this demo, the default per-run worktree/trusted-home layout is provisioned there, and explicit overrides still take precedence.
- [x] 1.3 Add or update documentation/help text for the interactive demo defaults so the effective per-run worktree/home layout and demo-wide `-y` contract are clear.

## 2. Startup Recovery

- [x] 2.1 Add clean-slate startup reset for the canonical tutorial identity so `start` kills any existing `AGENTSYS-alice` session, cleans leftover tmux/demo state, and clears prior-run artifacts before launching the replacement session.
- [x] 2.2 Add demo-local fixed-loopback CAO replacement logic so `start` prompts before recycling an existing verified local `cao-server`, honors demo-wide `-y` as yes-to-all, and uses existing launcher primitives without modifying shared launcher code.
- [x] 2.3 Ensure startup fails or aborts safely with actionable diagnostics, leaves `state.json` inactive when confirmation is declined or the port occupant is not a verified `cao-server`, and does not silently reuse stale fixed-port CAO state.

## 3. Automated Coverage

- [x] 3.1 Extend unit tests for repo-root-anchored demo defaults, per-run worktree/trusted-home provisioning, demo-wide `-y` flag handling, and clean-slate tutorial reset behavior.
- [x] 3.2 Extend integration coverage for prompt-confirmed CAO replacement, `-y` bypass behavior, unverifiable port-occupant failure, and fresh-start artifact cleanup.
- [x] 3.3 Re-run the interactive demo validation flow after implementation and confirm the default wrapper path now uses the per-run worktree/home layout without requiring manual CAO cleanup or launcher-home overrides.
