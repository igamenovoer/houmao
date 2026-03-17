## ADDED Requirements

### Requirement: Repository SHALL provide tracked dummy-project fixtures for narrow runtime-agent tests
The repository SHALL include tracked dummy projects under `tests/fixtures/dummy-projects/` for mailbox, prompt-turn, and other runtime-agent tests that do not require the main repository checkout as the launched working directory.

At least one tracked dummy project SHALL be suitable for mailbox tutorial/demo automation and SHALL contain only a small bounded Python-oriented tree plus the minimal docs or tests needed to make the workspace realistic for Claude Code and Codex.

Each dummy project fixture SHALL be designed so a test or demo helper can copy it into a run-local path and use that copied directory as a standalone git-backed workdir without creating a git worktree of the main repository.

#### Scenario: Maintainer can discover a mailbox-ready dummy project fixture
- **WHEN** a maintainer inspects `tests/fixtures/dummy-projects/`
- **THEN** the repository contains at least one tracked mailbox-ready dummy project fixture
- **AND THEN** that fixture is much smaller and narrower than the main repository checkout

#### Scenario: Copied dummy fixture becomes a standalone demo workdir
- **WHEN** a test or demo helper provisions the mailbox-ready dummy project into `<demo-output-dir>/project`
- **THEN** the resulting path is usable as a standalone git-backed workdir for that run
- **AND THEN** it is not a git worktree of the main repository
- **AND THEN** the launched agent workdir no longer needs to point at the main repository checkout

### Requirement: Repository SHALL provide lightweight mailbox-demo agent definitions separate from heavyweight engineering roles
The repository SHALL provide a dedicated lightweight role family for mailbox/demo/runtime-contract tests under `tests/fixtures/agents/roles/`.

Those lightweight roles SHALL explicitly bias the agent toward the requested mailbox or runtime-contract action over broad project discovery. They SHALL avoid unrelated benchmarking, CUDA, or large-repo exploration guidance unless a specific fixture explicitly needs that behavior.

The repository SHALL also provide dedicated mailbox-demo Claude/Codex brain recipes and blueprints that bind the normal tool adapters to those lightweight roles instead of to the heavyweight GPU-oriented role family.

#### Scenario: Maintainer can select dedicated mailbox-demo blueprints
- **WHEN** a maintainer inspects the tracked agent fixtures for the mailbox tutorial/demo flow
- **THEN** dedicated Claude and Codex mailbox-demo blueprints exist alongside the heavyweight engineering blueprints
- **AND THEN** those blueprints resolve to the lightweight mailbox-demo role family rather than to the GPU-oriented role family

### Requirement: Fixture guidance SHALL distinguish dummy-project and lightweight-role usage from repo-worktree and heavyweight-role usage
The repository fixture documentation SHALL explain when a test or demo should use:

- a copied dummy-project workdir instead of a repo worktree, and
- a lightweight mailbox/demo role instead of a heavyweight engineering role.

That guidance SHALL make clear that dummy projects and lightweight roles are the default choice for narrow runtime-contract or mailbox-turn coverage, while repo-scale worktrees and heavyweight roles remain appropriate for workflows that intentionally test broad engineering behavior.

#### Scenario: Fixture documentation explains the selection boundary
- **WHEN** a maintainer reads the tracked fixture guidance
- **THEN** the documentation distinguishes narrow runtime/mailbox coverage from repo-scale engineering coverage
- **AND THEN** it tells the maintainer when to choose dummy-project/lightweight-role fixtures versus repo-worktree/heavyweight-role fixtures
