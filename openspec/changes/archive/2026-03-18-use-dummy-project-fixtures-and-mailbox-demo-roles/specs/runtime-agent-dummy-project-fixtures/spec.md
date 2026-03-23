## ADDED Requirements

### Requirement: Repository SHALL provide tracked dummy-project fixtures for narrow runtime-agent tests
The repository SHALL include tracked dummy projects under `tests/fixtures/dummy-projects/` for mailbox, prompt-turn, and other runtime-agent tests that do not require the main repository checkout as the launched working directory.

At least one tracked dummy project SHALL be suitable for mailbox tutorial/demo automation and SHALL contain a concrete tiny Python-oriented starter tree with a small implementation module, a small test module, and a README-level document so the workspace is realistic for Claude Code and Codex without inviting repo-scale discovery.

Each dummy project fixture SHALL remain source-only in the tracked repository. A test or demo helper SHALL copy that source tree into a run-local path and initialize the copied directory as a fresh standalone git-backed workdir rather than by creating a git worktree of the main repository or by copying tracked `.git` metadata.

#### Scenario: Maintainer can discover a mailbox-ready dummy project fixture
- **WHEN** a maintainer inspects `tests/fixtures/dummy-projects/`
- **THEN** the repository contains at least one tracked mailbox-ready dummy project fixture
- **AND THEN** that fixture is much smaller and narrower than the main repository checkout

#### Scenario: Copied dummy fixture becomes a standalone demo workdir
- **WHEN** a test or demo helper provisions the mailbox-ready dummy project into `<demo-output-dir>/project`
- **THEN** the resulting path is usable as a standalone git-backed workdir for that run
- **AND THEN** the helper initialized that copied path as a fresh git repository after copying the tracked source tree
- **AND THEN** it is not a git worktree of the main repository
- **AND THEN** the launched agent workdir no longer needs to point at the main repository checkout

### Requirement: Repository SHALL provide lightweight mailbox-demo agent definitions separate from heavyweight engineering roles
The repository SHALL provide a dedicated lightweight role family for mailbox/demo/runtime-contract tests under `tests/fixtures/agents/roles/`.

Those lightweight roles SHALL explicitly bias the agent toward the requested mailbox or runtime-contract action over broad project discovery. They SHALL avoid unrelated benchmarking, CUDA, or large-repo exploration guidance unless a specific fixture explicitly needs that behavior.

The repository SHALL also provide dedicated mailbox-demo Claude/Codex brain recipes named `claude/mailbox-demo-default.yaml` and `codex/mailbox-demo-default.yaml`, plus blueprints named `mailbox-demo-claude.yaml` and `mailbox-demo-codex.yaml`, that bind the normal tool adapters to those lightweight roles instead of to the heavyweight GPU-oriented role family.

#### Scenario: Maintainer can select dedicated mailbox-demo blueprints
- **WHEN** a maintainer inspects the tracked agent fixtures for the mailbox tutorial/demo flow
- **THEN** dedicated `mailbox-demo-claude.yaml` and `mailbox-demo-codex.yaml` blueprints exist alongside the heavyweight engineering blueprints
- **AND THEN** those blueprints resolve to the lightweight mailbox-demo role family rather than to the GPU-oriented role family

### Requirement: Fixture guidance SHALL distinguish dummy-project and lightweight-role usage from repo-worktree and heavyweight-role usage
The repository fixture documentation SHALL explain when a test or demo should use:

- a copied dummy-project workdir instead of a repo worktree, and
- a lightweight mailbox/demo role instead of a heavyweight engineering role.

That guidance SHALL make clear that dummy projects and lightweight roles are the default choice for narrow runtime-contract or mailbox-turn coverage, while repo-scale worktrees and heavyweight roles remain appropriate for workflows that intentionally test broad engineering behavior.

The guidance SHALL include a short selection rubric or decision tree that helps maintainers choose between the two fixture families quickly.

#### Scenario: Fixture documentation explains the selection boundary
- **WHEN** a maintainer reads the tracked fixture guidance
- **THEN** the documentation distinguishes narrow runtime/mailbox coverage from repo-scale engineering coverage
- **AND THEN** it tells the maintainer when to choose dummy-project/lightweight-role fixtures versus repo-worktree/heavyweight-role fixtures
