## ADDED Requirements

### Requirement: Mailbox tutorial runner SHALL accept one demo-owned output directory
The mailbox roundtrip tutorial-pack runner SHALL accept a `--demo-output-dir <path>` option that selects the demo-owned output root for the run. When the option is omitted, the runner SHALL default to a repo-local directory under `tmp/demo/mailbox-roundtrip-tutorial-pack`.

If `--demo-output-dir` is relative, the runner SHALL resolve it from the repository root.

The selected demo output directory SHALL contain the demo-owned runtime root, shared mailbox root, copied inputs, captured command outputs, and generated reports.

#### Scenario: Runner uses the default demo output directory
- **WHEN** a developer runs `scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh` without `--demo-output-dir`
- **THEN** the runner selects a repo-local output directory under `tmp/demo/mailbox-roundtrip-tutorial-pack`
- **AND THEN** runtime artifacts, copied inputs, and reports are written under that selected demo output directory

#### Scenario: Runner honors an explicit relative demo output directory
- **WHEN** a developer runs the tutorial pack with `--demo-output-dir demos/manual-mailbox-run`
- **THEN** the runner resolves that relative path from the repository root
- **AND THEN** the resulting demo-owned artifacts are written under the resolved directory

### Requirement: Mailbox tutorial runner SHALL provision a nested project worktree and use it as both agents' workdir
The mailbox roundtrip tutorial-pack runner SHALL provision `<demo-output-dir>/project` as a git worktree of the main repository and SHALL use that `project/` directory as the `--workdir` passed to both `start-session` calls.

If `<demo-output-dir>/project` already exists as a valid git worktree, the runner MAY reuse it. If that path exists but is not a git worktree, the runner SHALL fail clearly instead of reusing or mutating it implicitly.

#### Scenario: Runner provisions a project worktree for agent startup
- **WHEN** a developer runs the tutorial pack and `<demo-output-dir>/project` does not yet exist
- **THEN** the runner provisions `<demo-output-dir>/project` as a git worktree of the main repository
- **AND THEN** both tutorial agents are started with `--workdir <demo-output-dir>/project`

#### Scenario: Runner rejects an incompatible existing project directory
- **WHEN** `<demo-output-dir>/project` already exists but is not a valid git worktree
- **THEN** the runner fails with a clear error
- **AND THEN** it does not silently reuse the incompatible directory as an agent workdir

### Requirement: Mailbox tutorial runner SHALL keep mailbox and runtime roots separate from the agent project workdir
The mailbox roundtrip tutorial-pack runner SHALL place the shared mailbox root and runtime root under the selected demo output directory while keeping the agent workdir pointed at the nested `project/` worktree.

The runner SHALL configure both agents to use the same shared mailbox root under `<demo-output-dir>/shared-mailbox`.

#### Scenario: Demo layout separates project workdir from mailbox and runtime state
- **WHEN** a developer runs the tutorial pack successfully
- **THEN** both agents use `<demo-output-dir>/project` as their workdir
- **AND THEN** both agents use one shared mailbox root under `<demo-output-dir>/shared-mailbox`
- **AND THEN** runtime-owned session artifacts remain under `<demo-output-dir>/runtime`

### Requirement: Mailbox tutorial runner SHALL support an optional demo-local jobs-root override
The mailbox roundtrip tutorial-pack runner SHALL accept a `--jobs-dir <path>` option that redirects both sessions' jobs-root base for the demo run. When `--jobs-dir` is omitted, the runner SHALL preserve Houmao's default job-dir derivation from the selected agent workdir.

If `--jobs-dir` is relative, the runner SHALL resolve it from the repository root.

When `--jobs-dir` is omitted, the resulting session job directories SHALL remain under:

`<demo-output-dir>/project/.houmao/jobs/<session-id>/`

#### Scenario: Omitted jobs-dir keeps Houmao default behavior
- **WHEN** a developer runs the tutorial pack without `--jobs-dir`
- **THEN** the runner does not override Houmao's local jobs-root selection
- **AND THEN** each started session resolves its `job_dir` under `<demo-output-dir>/project/.houmao/jobs/<session-id>/`

#### Scenario: Explicit jobs-dir redirects both sessions
- **WHEN** a developer runs the tutorial pack with `--jobs-dir tmp/demo/mailbox-jobs`
- **THEN** the runner resolves that path from the repository root
- **AND THEN** both launched sessions derive their per-session `job_dir` values from the resolved jobs-root base instead of from `<demo-output-dir>/project/.houmao/jobs`

### Requirement: Tutorial documentation and report artifacts SHALL reflect the demo-output-dir layout
The mailbox roundtrip tutorial-pack README, example commands, appendix inventory, and expected-report sanitization behavior SHALL reflect the distinction between:

- the demo output directory,
- the nested `project/` worktree used as agent workdir,
- the shared mailbox root,
- the runtime root, and
- default or relocated job-dir paths.

#### Scenario: README explains the revised filesystem layout
- **WHEN** a developer follows the updated tutorial README
- **THEN** the document names `--demo-output-dir` as the wrapper option
- **AND THEN** it explains that both agents use `<demo-output-dir>/project` as workdir
- **AND THEN** it distinguishes mailbox, runtime, and jobs-root placement from the project worktree

#### Scenario: Sanitized report masks demo-layout-specific paths
- **WHEN** a maintainer generates or refreshes the tutorial pack's sanitized report
- **THEN** demo-output-dir, project worktree, runtime-root, mailbox-root, and job-dir path values are masked consistently
- **AND THEN** the expected report remains reproducible across different local directories
