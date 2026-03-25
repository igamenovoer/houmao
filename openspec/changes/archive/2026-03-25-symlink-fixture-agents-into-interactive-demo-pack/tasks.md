## 1. Demo asset layout

- [x] 1.1 Replace `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents` with a tracked relative symlink to `tests/fixtures/agents/`.
- [x] 1.2 Remove or update any demo-pack files that still describe `agents/` as a separately maintained demo-owned asset tree.

## 2. Demo startup and documentation

- [x] 2.1 Update the interactive demo implementation and shell-facing documentation so startup still uses the demo-local `agents` path while describing it as a symlinked fixture-backed source.
- [x] 2.2 Review related repository docs or guidance that mention the interactive demo pack's agent-definition source and align that wording with the new symlink contract.

## 3. Automated coverage

- [x] 3.1 Update demo-focused unit or integration tests to assert that `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents` exists as a symlink resolving to `tests/fixtures/agents/`.
- [x] 3.2 Run the relevant demo-focused test coverage and any targeted checks needed to confirm startup still works through the unchanged demo-local `agents` path.
