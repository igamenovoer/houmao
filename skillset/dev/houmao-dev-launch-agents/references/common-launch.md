# Common Development Launch Contract

## Workflow

1. **Resolve inputs.** Confirm provider, trusted workdir, launch posture, unique tmux session name, and optional provider arguments.
2. **Create a fresh run root.** Use `tmp/houmao-dev-launch-agents/<UTC timestamp>-<provider>/` without reusing a non-empty directory.
3. **Preflight shared tools.** Require `tmux`, the selected provider executable, and a credential strategy that passes its provider gate.
4. **Build a secret-free launch command.** Put secret loading inside a restricted helper when required.
5. **Launch and verify.** Check tmux authority, provider process identity, and visible startup posture.
6. **Write launch metadata and report the attach command.** Preserve failures and clean up only resources owned by this run.

If a requested launch needs generated Houmao state, gateway attachment, recording, or a managed profile, use the native planning tool to select the maintained harness alternative below while preserving the same provider, workdir, secret, and verification boundaries.

## Required Inputs

- Provider subcommand
- Trusted workdir, defaulting to the repository root
- Prompt posture: `unattended` by default or explicit `as_is`
- Unique tmux session name, defaulting to `HMDEV-<provider>-<UTC timestamp>`
- Optional model, initial prompt, resume option, or provider-native arguments supplied by the user

Do not guess a model, resume target, extra writable directory, or initial prompt. Do not reinterpret unattended posture as a headless request.

## Guidance

Read this section as the shared execution procedure. Each step leaves inspectable launch evidence for the provider page and final report.

1. **Resolve the repository root.** Use the current Git worktree root and reject an untrusted or missing workdir.
2. **Reserve run identity.** Create a fresh run root and a tmux session name that does not exist according to `tmux has-session -t <name>`.
3. **Capture non-secret preflight.** Record provider command path, `--version` output, workdir, launch posture, credential strategy name, and source path or variable names without values.
4. **Assemble the command.** Quote each non-secret argument and keep secret resolution inside the child environment. For a `.env` route, create a run-local helper with mode `0700` that reads only the selected assignments as data and then `exec`s the provider.
5. **Start tmux.** Use one detached session with the workdir set by tmux and one provider process as the pane command.
6. **Verify bounded startup.** Poll for a short bounded interval until the pane exists, the provider process remains alive, and the visible pane shows a provider startup surface; fail with captured pane diagnostics when the process exits.
7. **Persist metadata.** Write `launch.json` and `launch-report.md`, excluding secrets, then return `tmux attach-session -t <name>`.

## Tmux Command Shape

Construct one safely quoted shell command and pass it as the tmux pane command:

```bash
tmux new-session -d \
  -s "<unique-session-name>" \
  -c "<trusted-workdir>" \
  "exec <selected-launcher> <provider-arguments>"
```

For a run-local helper, the final pane command is `exec <run-root>/launch-provider.sh <provider-arguments>`. The helper may read a trusted secret source internally; the tmux command and metadata must not contain the values.

## Preferences

Read these preferences as defaults. Record the reason whenever the selected route differs.

- Prefer TUI launch in detached tmux (if the user asks for headless execution, use the provider's headless surface outside this skill).
- Prefer `unattended` for automated development and testing (if the user explicitly asks for normal permission prompts, use `as_is`).
- Prefer a new session name (if the requested name exists, derive another name rather than replacing it).
- Prefer direct raw provider launch for ordinary TUI observation (if generated Houmao assets or gateway behavior are under test, use a maintained harness).

## Constraints

Read these constraints as validity boundaries. `Must` and `must not` requirements are hard gates.

- The workdir must exist and be trusted before an unattended launch.
- The launch command must not contain secret values.
- The run must not kill, reuse, or modify a tmux session it does not own.
- A provider login command must not run as part of auto credential discovery.
- Failed launches must retain non-secret diagnostics and must not be reported as live.
- Cleanup must target only the recorded tmux session and run-local helpers.

## Quality Gates

Read these gates after startup and before claiming success. Weak metrics or failed checks require diagnosis, retry under a new session identity, or a blocker report.

### Metrics

- Startup latency: elapsed time from tmux creation to a stable provider surface; lower is better, but correctness is primary.
- Evidence completeness: fraction of required non-secret metadata fields present; more complete is better.
- Unexpected prompt count: confirmation or login prompts under unattended mode; lower is better and zero is expected.

### Checks

- Session authority: the recorded tmux session exists and matches the selected name.
- Process identity: the pane process tree contains the selected provider launcher or its expected provider child.
- Surface readiness: captured visible pane text is non-empty and consistent with the selected CLI rather than a shell error.
- Secret hygiene: metadata and command text contain no credential values.
- Attachability: `tmux attach-session -t <name>` addresses the live session.

## Maintained Houmao Harness Alternatives

Use these only when their owned behavior is the test subject:

- Minimal generated-home launch: `scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code|codex`
- Shared TUI tracking live watch: `scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh start --tool claude|codex|kimi`
- Recorder-backed capture: use the `houmao-dev-tui-testing` skill, which composes the shared TUI tracking demo and terminal recorder
- Plain agent-definition experiment: copy `tests/fixtures/plain-agent-def/` and selected `tests/fixtures/auth-bundles/` content into a fresh run-local tree

Never route new work through `scripts/demo/legacy/`, historical `brains/`, `blueprints/`, or `api-creds` trees.

## Launch Metadata

`launch.json` contains only:

- schema version and run ID
- provider and provider version
- workdir and run root
- tmux session and pane identity
- launcher command name and resolved path
- credential strategy name
- credential source path and variable names when applicable, without values
- requested posture and non-secret provider arguments
- startup verification status and diagnostics paths
