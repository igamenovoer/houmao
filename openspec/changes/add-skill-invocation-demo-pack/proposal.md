## Why

Issue-008 exposed a gap between how Houmao installs skills and how maintainers can prove those skills are actually invokable by real Claude Code and Codex sessions. Today the repository has no self-contained demo that answers the concrete question "if Houmao installs a skill into the tool runtime home, will the live agent invoke it from ordinary prompt wording without being told the skill path or name?".

We need a maintainer-friendly, repeatable demo path for that contract, plus a tracked reusable dummy skill fixture that other tests and demos can reuse instead of inventing one-off probe skills.

## What Changes

- Add a new self-contained demo pack under `scripts/demo/skill-invocation-demo-pack/` that follows the local demo-pack pattern already used in `scripts/demo/`.
- Make the demo pack support both a one-shot `auto` path and an inspectable stepwise flow for both Claude Code and Codex rather than hard-coding one tool lane.
- Add a tracked reusable dummy skill fixture that performs a deterministic visible side effect when the agent invokes it, such as writing a marker file into a designated output directory.
- Make the demo verify skill invocation by prompting the agent with trigger wording only, without naming the skill and without referencing the skill install path.
- Add tracked skill-invocation demo recipes, blueprints, and fixture guidance so the demo can use a small dummy project and a lightweight role instead of repo-scale engineering prompts.
- Keep the live demo on the current CAO `shadow_only` posture and use the marker side effect, not authoritative reply text, as the success boundary.
- Make the supported CAO ownership model explicit so the first version uses the repo's launcher-managed loopback CAO pattern and `SKIP:` guidance rather than guessing about external CAO ownership.
- Document the operator workflow, expected outputs, and verification boundary so maintainers can use the demo to diagnose tool-specific skill-resolution behavior.

## Capabilities

### New Capabilities
- `skill-invocation-demo-pack`: A self-contained demo pack under `scripts/demo/` for one-shot and stepwise live verification of real Claude/Codex skill invocation through prompt-triggered side effects.

### Modified Capabilities
- `runtime-agent-dummy-project-fixtures`: Extend the tracked lightweight fixture family to include reusable dummy skill fixtures and skill-invocation demo definitions alongside the existing dummy-project and lightweight-role guidance.

## Impact

- `scripts/demo/skill-invocation-demo-pack/` new demo pack, including `README.md`, `run_demo.sh`, inputs, verification helpers, and expected report snapshot(s)
- `tests/fixtures/agents/brains/skills/` for the tracked reusable dummy skill fixture
- `tests/fixtures/agents/brains/brain-recipes/`, `tests/fixtures/agents/roles/`, and `tests/fixtures/agents/blueprints/` for lightweight skill-invocation demo definitions
- likely `tests/fixtures/dummy-projects/` reuse rather than repo-worktree launch
- documentation around skill installation and invocation verification
- follow-up tests or automation that can reuse the same dummy skill fixture
