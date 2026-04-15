## Why

Houmao's managed-agent memory contract has become too broad: it exposes a generic workspace with scratch and persist lanes even though Claude, Codex, and similar CLIs already manage their own internal context, and durable work artifacts usually belong in the launched workdir or an operator-selected project directory. Houmao should own one small, obvious memory surface: a memo file plus indexed pages.

## What Changes

- **BREAKING** Replace the current managed-agent workspace envelope with a simplified managed-agent memory directory rooted by default at `<active-overlay>/memory/agents/<agent-id>/`.
- **BREAKING** Remove the `scratch/` and `persist/` lane model from managed-agent memory. Houmao no longer treats this directory as a generic scratch workspace, artifact archive, or external persist binding surface.
- Create exactly one managed subdirectory under each agent memory root: `pages/`.
- Keep `houmao-memo.md` as the fixed top-level memo file and make it the human/agent-readable index for page content under `pages/`.
- Publish a narrower live environment contract:
  - `HOUMAO_AGENT_MEMORY_DIR` points to the memory root.
  - `HOUMAO_AGENT_MEMO_FILE` points to `houmao-memo.md`.
  - `HOUMAO_AGENT_PAGES_DIR` points to `pages/`.
- **BREAKING** Remove `HOUMAO_AGENT_STATE_DIR`, `HOUMAO_AGENT_SCRATCH_DIR`, and `HOUMAO_AGENT_PERSIST_DIR` from the current managed-memory contract.
- **BREAKING** Remove managed launch/profile persistence controls such as `--persist-dir`, `--no-persist-dir`, stored `persist_dir`, and stored `persist_disabled`; operators should use the launched workdir or explicit project paths for work artifacts.
- Replace lane-scoped CLI, gateway, and pair-server workspace file operations with memo/page operations only.
- Add page indexing behavior so supported page mutations refresh the managed index section in `houmao-memo.md`, and a supported reindex operation can reconcile direct filesystem edits under `pages/`.
- Update loop and advanced-usage guidance so runtime ledgers do not default to a Houmao scratch lane; durable operator-visible loop context may be captured as readable memo pages when appropriate.

## Capabilities

### New Capabilities
- `agent-memory-pages`: Defines the simplified per-agent memory root, fixed memo file, `pages/` directory, page path containment, memo index behavior, live environment variables, CLI operations, gateway operations, and page-oriented lifecycle boundaries.

### Modified Capabilities
- `agent-workspace-dirs`: Replace the scratch/persist workspace envelope with the memo/pages memory model.
- `agent-memory-dir`: Remove optional persist-lane binding semantics in favor of always-created memo/pages memory roots.
- `brain-launch-runtime`: Persist and publish `memory_root`, `memo_file`, and `pages_dir` instead of workspace, scratch, and persist fields.
- `houmao-owned-dir-layout`: Update the Houmao-owned per-agent memory layout to contain only `houmao-memo.md` and `pages/`.
- `houmao-mgr-agents-launch`: Remove persist controls from launch and report the simplified memory paths in launch output.
- `houmao-mgr-agents-join`: Remove persist controls from join and publish the simplified memory paths for adopted sessions.
- `agent-launch-profiles`: Remove stored persist-lane defaults from reusable launch-profile behavior.
- `houmao-mgr-project-agents-launch-profiles`: Remove persist controls from explicit launch-profile authoring and inspection.
- `houmao-mgr-project-easy-cli`: Remove persist controls from easy profiles and easy instance launches.
- `houmao-mgr-cleanup-cli`: Remove scratch-lane cleanup as a managed-agent memory operation.
- `agent-gateway`: Replace lane-scoped workspace endpoints with memo/page endpoints.
- `passive-server-gateway-proxy`: Proxy the simplified gateway memo/page endpoints instead of lane-scoped workspace endpoints.
- `managed-agent-detailed-state`: Report memory root, memo file, and pages directory instead of scratch/persist workspace fields.
- `houmao-adv-usage-pattern-skill`: Remove guidance that stores mutable loop ledgers in `HOUMAO_AGENT_SCRATCH_DIR`.
- `houmao-agent-loop-pairwise-v2-skill`: Keep initialization memo guidance, but target the simplified memo/pages memory surface.
- `system-files-reference-docs`: Update reference documentation to describe the simplified memory layout and ownership boundary.
- `docs-getting-started`: Update getting-started documentation to present managed-agent memory as memo plus indexed pages.

## Impact

- Runtime path helpers, session manifest models and schemas, launch/join flows, launch-plan environment injection, relaunch/resume behavior, registry/state projection, and inspection renderers.
- `houmao-mgr agents launch`, `agents join`, `agents memory` or renamed workspace commands, project launch-profile commands, easy profile and easy instance commands, and cleanup commands.
- Live gateway HTTP routes and pair-server proxy routes for managed-agent memory access.
- System skills and advanced usage pattern docs that currently reference scratch or persist lanes.
- Unit and integration coverage for path creation, env publication, manifest parsing, CLI output, gateway routes, page containment, memo indexing, and removal of persist controls.
