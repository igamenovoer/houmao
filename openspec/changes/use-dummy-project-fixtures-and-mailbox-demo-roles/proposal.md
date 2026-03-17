## Why

The current mailbox tutorial pack and related runtime-contract tests hand Claude Code and Codex a git worktree of the main repository together with heavyweight GPU-oriented roles. For narrow mailbox turns, that fixture shape is counterproductive: the agents spend time exploring a large repo and broad engineering instructions instead of performing the requested mailbox action, which makes real-agent runs slow, timeout-prone, and harder to diagnose.

The current spec and test split is also misleading. The tracked "direct live" automation lane uses owned fake CLI fixtures, but its requirement text still claims automatic coverage with real external agents. The repository needs a cleaner split between deterministic direct-path regression coverage and opt-in local smoke coverage with actual Claude/Codex sessions.

## What Changes

- Add tracked dummy-project fixtures plus lightweight mailbox-demo roles, recipes, and blueprints for narrow runtime-agent and mailbox-demo tests.
- Change the mailbox tutorial pack defaults so sender and receiver run inside a copied dummy project rooted under the demo-owned output/home tree instead of a git worktree of the main repository.
- Add a pack-owned inspect/watch surface so maintainers can periodically attach tmux, tail terminal logs, and view live tool state while slow mailbox turns are in flight.
- Keep the mailbox sentinel-delimited result contract strict; missing or malformed result blocks remain direct-path failures instead of being papered over by synthetic mailbox success.
- Split deterministic automatic direct-path coverage from opt-in real-agent smoke coverage so the tracked automation contract stops claiming fake harnesses are real external agents.

## Capabilities

### New Capabilities
- `runtime-agent-dummy-project-fixtures`: tracked dummy projects, lightweight mailbox-demo/runtime roles, dedicated Claude/Codex blueprints, and fixture guidance for choosing dummy projects versus repo worktrees.
- `mailbox-roundtrip-real-agent-smoke`: an opt-in local smoke lane that uses actual Claude/Codex CLIs with the dummy-project/lightweight-role fixture shape and exposes in-flight inspection pointers.

### Modified Capabilities
- `mailbox-roundtrip-tutorial-pack`: change the default tutorial pair and workdir contract to use dummy-project fixtures and lightweight mailbox-demo blueprints instead of the main-repo worktree plus GPU roles.
- `mailbox-roundtrip-demo-automation`: extend the pack-local automation surface with an inspect/watch command that exposes tmux, terminal-log, and live tool-state diagnostics for the two tutorial sessions.
- `mailbox-roundtrip-direct-live-automation-test`: redefine the tracked automatic lane as an owned deterministic direct-path regression harness and move actual external-agent coverage into the new opt-in smoke capability.

## Impact

- Affected code: `scripts/demo/mailbox-roundtrip-tutorial-pack/`, `src/houmao/demo/`, runtime helper code that resolves tutorial-pack session state and inspection surfaces, and any helper paths that currently create a repo worktree for mailbox-demo sessions.
- Affected fixtures: `tests/fixtures/dummy-projects/`, `tests/fixtures/agents/roles/`, `tests/fixtures/agents/brain-recipes/`, `tests/fixtures/agents/blueprints/`, and fixture README/guidance.
- Affected tests: tracked integration coverage under `tests/integration/demo/` plus a new opt-in/manual real-agent smoke lane under `tests/manual/` or equivalent env-gated entrypoint.
- Affected docs/specs: mailbox tutorial-pack docs, fixture guidance, and mailbox automation specs that currently imply real-agent automatic coverage or full-repo workdir defaults.
