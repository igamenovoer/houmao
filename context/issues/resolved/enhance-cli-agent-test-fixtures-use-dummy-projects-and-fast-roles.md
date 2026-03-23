# Enhancement Proposal: CLI-Agent Test Fixtures Should Use Dummy Projects And Lightweight Roles

## Status
Resolved on 2026-03-20.

## Resolution Summary
Tracked dummy projects now exist under `tests/fixtures/dummy-projects/`, lightweight runtime/demo roles such as `mailbox-demo` exist under `tests/fixtures/agents/roles/`, dedicated `mailbox-demo-{claude,codex}` blueprints bind those roles, and the mailbox tutorial/demo packs now provision copied dummy-project workdirs instead of defaulting to a worktree of the full repository.

## Summary
Several CAO-backed demo and test flows currently hand Claude Code and Codex a git worktree of this repository as their working directory while also assigning heavyweight GPU-performance roles from `tests/fixtures/agents/roles/`.

That combination is a poor fit for mailbox and runtime-contract tests:

- the working directory is large and full of attractive-but-irrelevant paths such as `src/`, `docs/`, `openspec/`, `extern/`, and historical context notes,
- the current role prompt encourages broad repo exploration, code changes, builds, benchmarking, and environment discovery,
- live mailbox/demo tests therefore spend substantial time crawling the repo instead of performing the narrow mailbox action the test actually wants to validate.

For fast runtime-contract tests, the harness should provide a much smaller test project plus lightweight roles that are explicitly optimized for bounded mailbox/demo behavior.

## Why
The current mailbox tutorial pack made this mismatch obvious:

- the pack provisions `<demo-output-dir>/project` as a git worktree of the repo,
- the sender/receiver blueprints currently bind to `gpu-kernel-coder` flavored roles,
- Claude and Codex both see a real repo with many legitimate directories to inspect,
- Claude especially tends to interpret the prompt as "understand the repo before acting",
- direct mail turns then become slow and timeout-prone even when the underlying CLI agent is functioning normally.

This is not primarily a parser problem. It is a fixture-design problem:

```text
current test fixture
    │
    ├── large repo worktree
    ├── heavyweight engineering role
    └── narrow mailbox task

result:
    agent explores too much before doing the mailbox operation
```

The harness should instead bias toward:

```text
desired test fixture
    │
    ├── tiny dummy project
    ├── lightweight mailbox/demo role
    └── narrow mailbox task

result:
    agent performs the requested operation quickly and reproducibly
```

## Proposed Direction
### 1. Add tracked dummy projects for runtime-agent tests
Introduce test-owned projects under:

```text
tests/fixtures/dummy-projects/<project-name>/
```

These projects should be intentionally small, realistic enough for CLI tools to feel grounded, and cheap to scan.

Examples:

- `tests/fixtures/dummy-projects/python-minimal-mailbox/`
- `tests/fixtures/dummy-projects/python-two-module-app/`
- `tests/fixtures/dummy-projects/python-config-and-tests/`

Each dummy project should:

- be a valid git repository or be easy for tests to snapshot into one,
- contain only a few Python files plus minimal docs/tests,
- avoid unrelated large trees and heavy dependency surfaces,
- be suitable as a working directory for mailbox, prompt-turn, and CAO runtime tests.

### 2. Add lightweight test roles under `tests/fixtures/agents/roles/`
Introduce simpler roles specifically for runtime/demo tests, separate from the GPU-kernel roles.

These roles should:

- explicitly forbid broad repo crawling unless required,
- tell the agent to prefer the mailbox/runtime task over project discovery,
- keep file reads bounded and local,
- avoid instructions about benchmarking, CUDA, `cpp/`, or unrelated build systems,
- bias toward short responses and deterministic command usage.

Possible role families:

- `mailbox-demo-worker`
- `runtime-contract-worker`
- `tiny-python-project-worker`

### 3. Bind new blueprints to those lightweight roles
Keep the current GPU-oriented blueprints for performance workflows, but add separate blueprints for fast runtime/demo tests.

Examples:

- `tests/fixtures/agents/blueprints/mailbox-demo-claude.yaml`
- `tests/fixtures/agents/blueprints/mailbox-demo-codex.yaml`

Those blueprints should resolve to:

- the same tool-specific brain recipe layer when appropriate,
- a lightweight test role rather than `gpu-kernel-coder`.

### 4. Let tutorial/demo packs choose the smaller project fixture
Mailbox tutorial packs and similar live-runtime tests should stop defaulting to a worktree of the full repo when the test goal does not require it.

For mailbox/direct-turn automation, prefer:

- provisioning a test-owned worktree or copy derived from one dummy project fixture, or
- starting the agent directly in a dummy project fixture root,

instead of pointing the session at a worktree of the whole repository.

### 5. Preserve repo-worktree coverage only where it is actually needed
Some tests should still exercise "real repo worktree" behavior. That coverage is valuable, but it should be explicit and narrower.

The fixture model should split these concerns:

- fast mailbox/runtime contract tests use dummy projects,
- repo-scale exploration behavior is covered by dedicated tests that intentionally use the main repo worktree.

## Acceptance Criteria
1. The repository contains tracked dummy projects under `tests/fixtures/dummy-projects/` for narrow runtime-agent tests.
2. At least one dummy project is suitable as the working directory for mailbox tutorial/demo automation.
3. `tests/fixtures/agents/roles/` contains lightweight test roles that are explicitly optimized for narrow demo/runtime tasks.
4. `tests/fixtures/agents/blueprints/` contains dedicated fast-test blueprints that use those lightweight roles instead of the GPU-kernel roles.
5. Mailbox tutorial/demo automation can be configured to use a dummy-project working directory rather than a worktree of the full repository.
6. Live mailbox/runtime tests stop relying on heavyweight repo discovery as part of their normal pass path.
7. Docs explain when to use:
   - real-repo worktrees,
   - dummy-project fixtures,
   - heavyweight engineering roles,
   - lightweight demo/runtime roles.

## Likely Touch Points
- `tests/fixtures/dummy-projects/`
- `tests/fixtures/agents/roles/`
- `tests/fixtures/agents/blueprints/`
- `tests/fixtures/agents/README.md`
- `scripts/demo/mailbox-roundtrip-tutorial-pack/README.md`
- `scripts/demo/mailbox-roundtrip-tutorial-pack/scripts/tutorial_pack_helpers.py`
- live demo/runtime tests under `tests/integration/demo/`

## Non-Goals
- No requirement to remove repo-worktree coverage entirely.
- No requirement to replace all existing agent roles.
- No requirement to make dummy projects perfectly realistic beyond what runtime/demo tests need.
- No requirement to solve every slow-agent case purely through parser changes.

## Suggested Follow-Up
1. Create an OpenSpec change for "dummy test projects + lightweight runtime roles".
2. Decide whether demo packs should use fixture copies, fixture worktrees, or direct fixture roots as the agent workdir.
3. Define one minimal mailbox/demo role contract that both Claude and Codex can follow consistently.
4. Audit existing live tests and reclassify them into:
   - "needs real repo worktree"
   - "should use dummy project"
