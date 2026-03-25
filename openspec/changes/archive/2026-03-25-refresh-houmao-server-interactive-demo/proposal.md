## Why

The `houmao-server-interactive-full-pipeline-demo` pack has drifted from current repository reality. Its checked-in `agents/` tree is a copied snapshot instead of the spec-required tracked symlink to `tests/fixtures/agents/`, and its docs/help/spec wording still describe older `houmao-mgr cao launch` behavior even though the Python demo implementation already launches through the demo-owned `houmao-server` native headless launch API.

Now that `revise-houmao-mgr-cli-shape` is complete, the demo needs a focused follow-up that refreshes its artifacts without mixing in a second launch-model rewrite.

## What Changes

- Replace `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents` with a repository-tracked symlink to `tests/fixtures/agents/`.
- Refresh the demo README, shell-wrapper help text, and Python demo CLI/help strings so they describe the current server-backed launch path instead of the retired `houmao-mgr cao launch` wording.
- Update the demo specification to describe the actual startup contract: demo-owned `houmao-server`, native headless launch API, persisted `houmao_server` manifest bridge, and HTTP-only follow-up control flow.
- Keep the documented demo-owned create-timeout override meaningful by routing it through the current native launch client instead of leaving a stale compatibility-only knob.
- Preserve the current server-backed runtime model for the demo and explicitly keep migration to local `houmao-mgr agents launch` out of scope for this change.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `houmao-server-interactive-full-pipeline-demo`: Refresh the startup and layout requirements so the demo's documented contract matches the current implementation and the shipped `agents` entry is the tracked symlink required by the main spec.

## Impact

- `scripts/demo/houmao-server-interactive-full-pipeline-demo/agents`
- `scripts/demo/houmao-server-interactive-full-pipeline-demo/README.md`
- `scripts/demo/houmao-server-interactive-full-pipeline-demo/run_demo.sh`
- `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/cli.py`
- `src/houmao/demo/houmao_server_interactive_full_pipeline_demo/commands.py`
- `openspec/specs/houmao-server-interactive-full-pipeline-demo/spec.md`
- Demo validation coverage and any tests that assert the demo pack layout or startup wording
