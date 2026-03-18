## Why

Issue-008 exposed a gap between how Houmao installs skills and how maintainers can prove those skills are actually invokable by real Claude Code and Codex sessions. Today the repository has no self-contained demo that answers the concrete question "if Houmao installs a skill into the tool runtime home, will the live agent invoke it from ordinary prompt wording without being told the skill path or name?".

We need a maintainer-friendly, repeatable demo path for that contract, plus a tracked reusable dummy skill fixture that other tests and demos can reuse instead of inventing one-off probe skills.

## What Changes

- Add a new self-contained demo pack under `scripts/demo/skill-invocation-demo-pack/` that follows the local demo-pack pattern already used in `scripts/demo/`.
- Make the demo pack support interactive, stepwise testing for both Claude Code and Codex agents rather than hard-coding one tool lane.
- Add a tracked reusable dummy skill fixture that performs a deterministic visible side effect when the agent invokes it, such as writing a marker file into a designated output directory.
- Make the demo verify skill invocation by prompting the agent with trigger wording only, without naming the skill and without referencing the skill install path.
- Add fixture-level role/blueprint guidance for this narrow skill-invocation contract so the demo can use a small dummy project and a lightweight role instead of repo-scale engineering prompts.
- Document the operator workflow, expected outputs, and verification boundary so maintainers can use the demo to diagnose tool-specific skill-resolution behavior.

## Capabilities

### New Capabilities
- `skill-invocation-demo-pack`: A self-contained demo pack under `scripts/demo/` for interactively and automatically verifying real Claude/Codex skill invocation through prompt-triggered side effects.

### Modified Capabilities
- `runtime-agent-dummy-project-fixtures`: Extend the tracked lightweight fixture family to include reusable dummy skill fixtures and skill-invocation demo definitions alongside the existing dummy-project and lightweight-role guidance.

## Impact

- `scripts/demo/skill-invocation-demo-pack/` new demo pack, including `README.md`, `run_demo.sh`, inputs, verification helpers, and expected report snapshot(s)
- `tests/fixtures/agents/brains/skills/` for the tracked reusable dummy skill fixture
- `tests/fixtures/agents/roles/` and `tests/fixtures/agents/blueprints/` for lightweight skill-invocation demo definitions
- likely `tests/fixtures/dummy-projects/` reuse rather than repo-worktree launch
- documentation around skill installation and invocation verification
- follow-up tests or automation that can reuse the same dummy skill fixture
