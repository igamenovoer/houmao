## MODIFIED Requirements

### Requirement: Tutorial-pack runner SHALL follow self-contained execution mechanics
The tutorial-pack `run_demo.sh` SHALL:

- use robust shell mode (`set -euo pipefail`),
- define repository context and a temporary workspace path,
- check prerequisites before execution,
- copy tracked demo inputs into the temporary workspace before runtime commands execute,
- copy a tracked source-only dummy-project fixture into the demo-local `project/` workdir and initialize the copied tree as a fresh git-backed workspace before runtime commands execute, and
- support `--snapshot-report` mode for expected-report refresh.

The tracked demo parameters SHALL define the default tutorial pair, including:

- `tests/fixtures/agents/roles/mailbox-demo/presets/claude/default.yaml` as the lightweight mailbox-demo Claude preset,
- `tests/fixtures/agents/roles/mailbox-demo/presets/codex/default.yaml` as the lightweight mailbox-demo Codex preset,
- the CAO-backed backend choice,
- agent identities,
- mailbox principal/address pairs,
- message body file references, and
- the selected dummy-project fixture.

The runner SHALL avoid modifying tracked files outside explicit snapshot mode.

#### Scenario: Runner prepares an isolated workspace from tracked inputs and a dummy project fixture
- **WHEN** a developer runs `run_demo.sh`
- **THEN** the runner creates an isolated workspace and copies the tracked tutorial inputs into it before the mailbox workflow starts
- **AND THEN** it provisions the selected dummy-project fixture into the demo-local `project/` workdir and initializes that copied tree as a fresh git-backed workspace before any `start-session` call
- **AND THEN** the default tutorial parameters reference the tracked mailbox-demo presets rather than the heavyweight GPU-oriented tutorial pair

### Requirement: Tutorial-pack runner SHALL start two mailbox-enabled sessions on one shared mailbox root
The tutorial-pack runner SHALL build and start two CAO-backed runtime sessions that both use mailbox support against the same filesystem mailbox root while keeping distinct agent identities, mailbox principal ids, and mailbox addresses.

The runner SHALL use preset-backed build and start flow for the tutorial pair, with default auth selection owned by the selected presets and mailbox enablement expressed through `start-session --mailbox-*` overrides rather than tutorial-specific mailbox configuration in legacy recipe or blueprint files.

The runner SHALL pass the provisioned dummy-project workdir under the selected demo-owned output/home tree to both `start-session` calls instead of targeting a git worktree of the main repository.

The runner SHALL ensure that copied `project/` tree is initialized as its own fresh git repository rather than as a worktree or a copied tracked `.git/` directory.

The runner SHALL capture the structured `start-session` output for both agents, including the redacted mailbox binding payload returned by the runtime.

The runner SHALL keep demo-specific persistent state minimal and SHALL rely on the runtime's name-addressed tmux/manifest recovery path for follow-up `mail` and `stop-session` targeting whenever that native mechanism is sufficient.

#### Scenario: Two tutorial agents join the same mailbox root from the dummy-project workdir
- **WHEN** a developer runs the tutorial pack with prerequisites satisfied
- **THEN** the pack starts two mailbox-enabled sessions that resolve to one shared mailbox root
- **AND THEN** each session receives its own mailbox principal id and mailbox address
- **AND THEN** both `start-session` calls use the provisioned dummy-project workdir under the selected demo-owned output/home tree
- **AND THEN** the run artifacts include the structured startup payloads for both sessions
- **AND THEN** the sessions were started through the tracked mailbox-demo presets with mailbox flags supplied on `start-session`
