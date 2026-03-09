## Why

The interactive CAO demo currently has the right high-level workflow, but its default startup path is not reliably runnable in real local environments. The default launcher home can reject the default repo workdir, healthy loopback `cao-server` reuse can preserve stale CAO home context, the helper scripts do not share a consistent confirmation contract, and stale `AGENTSYS-alice` state can block relaunches. A tutorial demo is supposed to be easy to run repeatedly, so startup needs to provision its own trusted workspace, recover cleanly from old local state, and make any destructive takeover explicit.

## What Changes

- Keep repo-root-derived omitted defaults inside the interactive demo pack and provision a per-run demo root under `tmp/demo/cao-interactive-full-pipeline-demo/<ts>/`, even when the caller invokes the demo from another `pwd`.
- Make default startup create a git worktree at `<repo-root>/tmp/demo/cao-interactive-full-pipeline-demo/<ts>/wktree` and use the enclosing per-run directory as the CAO trusted home so the effective workdir always remains inside the trusted tree.
- Add demo-local startup recovery that prompts before recycling an existing verified local `cao-server` on `127.0.0.1:9889`, while keeping non-CAO occupants as explicit failures.
- Make `-y` a consistent yes-to-all flag across `run_demo.sh`, `launch_alice.sh`, `send_prompt.sh`, and `stop_demo.sh`, even for commands that do not prompt today.
- Reset canonical `AGENTSYS-alice` session state and leftover demo artifacts before replacement startup so each run behaves like a fresh start.
- Expand automated coverage for cwd-independent defaults, startup recovery, and stale-state handling.

## Capabilities

### New Capabilities
- `cao-interactive-demo-startup-recovery`: deterministic, self-healing startup and default path behavior for the interactive CAO demo pack.

### Modified Capabilities
- None.

## Impact

- Affected code: `scripts/demo/cao-interactive-full-pipeline-demo/run_demo.sh`, `scripts/demo/cao-interactive-full-pipeline-demo/launch_alice.sh`, `scripts/demo/cao-interactive-full-pipeline-demo/send_prompt.sh`, `scripts/demo/cao-interactive-full-pipeline-demo/stop_demo.sh`, `src/gig_agents/demo/cao_interactive_full_pipeline_demo.py`, and related tests under `tests/unit/demo/` and `tests/integration/demo/`.
- Affected systems: local `tmux`, local loopback `cao-server` management at `http://127.0.0.1:9889`, repo-root path resolution, and CAO launcher/home alignment.
- Affected operator behavior: tutorial startup becomes more opinionated, uses a per-run worktree/home layout by default, prompts before replacing an existing verified local CAO server unless `-y` is supplied, and resets stale `AGENTSYS-alice` state before launching the new run.
