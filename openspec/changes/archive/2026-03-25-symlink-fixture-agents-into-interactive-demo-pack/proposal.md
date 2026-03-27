## Why

The interactive full-pipeline demo pack currently carries its own copied `agents/` tree even though the repository already maintains the canonical native agent-definition fixtures under `tests/fixtures/agents/`. Keeping both trees in sync creates avoidable drift and makes the demo contract heavier than necessary for a repo-owned workflow.

## What Changes

- Change the interactive full-pipeline demo-pack contract so `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents` is a tracked symlink to `tests/fixtures/agents/` instead of a separately maintained directory tree.
- Update the demo-pack documentation and requirement language to treat the shared fixture tree as the supported native launch source for this repo-owned demo.
- Adjust automated coverage so the demo verifies the presence and use of the symlinked `agents` path rather than asserting a demo-owned copied asset tree.

## Capabilities

### New Capabilities

### Modified Capabilities

- `houmao-server-interactive-full-pipeline-demo`: Change the demo-pack startup asset contract from a demo-owned non-test agent-definition tree to a demo-local `agents` entry that resolves to the tracked fixture tree through a symlink.

## Impact

- Affected code: `scripts/demo/houmao-server-interactive-full-pipeline-demo/`, the demo implementation under `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/`, and demo-specific tests.
- Affected docs: the demo README plus any repository guidance that currently describes the demo `agents/` tree as a standalone copied source.
- Affected systems: the interactive full-pipeline demo startup path, repository-owned native agent-definition fixture maintenance, and test/demo assertions around launch asset layout.
