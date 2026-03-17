## Why

The mailbox roundtrip tutorial pack currently launches both agents into one generic workspace directory, which makes the demo less realistic and less explicit about where agent-visible project files, mailbox state, runtime artifacts, and scratch job outputs belong. That makes interactive testing harder because operators do not get a real project checkout for the agents to inspect or modify, and the runner does not provide one obvious demo-owned output root to reuse or inspect.

## What Changes

- Add a demo-owned `--demo-output-dir <path>` wrapper option for `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh`, with a default repo-local output root under `tmp/demo/mailbox-roundtrip-tutorial-pack`.
- Make the runner provision `<demo-output-dir>/project` as a git worktree of the main repository, and use that nested `project/` directory as the `--workdir` passed to both agent `start-session` commands.
- Keep mailbox and runtime-owned demo artifacts explicit by placing the shared mailbox root, runtime root, copied inputs, captured JSON outputs, and reports under the selected demo output directory instead of conflating them with the agent workdir.
- Add a demo-owned `--jobs-dir <dir>` wrapper option that redirects both launched sessions to one caller-selected jobs root when desired, while preserving Houmao's current default job-dir behavior when the option is omitted.
- Update the tutorial README, expected-report sanitization rules, and runner/integration coverage so the documented filesystem layout and captured outputs reflect the new demo-output-dir/project-worktree contract.

## Capabilities

### New Capabilities
- `mailbox-roundtrip-demo-output-layout`: Defines the demo-owned output-directory, nested project worktree, and optional jobs-root behavior for the mailbox roundtrip tutorial pack.

### Modified Capabilities

## Impact

- Affected code: `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh`, its README and helper tooling, and demo-focused tests for runner behavior and sanitized report output.
- Affected systems: demo workspace layout, git worktree provisioning, runtime session `workdir` selection, demo-local jobs-root override behavior, and tutorial-pack reporting.
- Affected operator workflow: users launch the pack with `--demo-output-dir` rather than reasoning about one generic workspace path, and they inspect a nested `project/` worktree as the agent-visible repository checkout.
