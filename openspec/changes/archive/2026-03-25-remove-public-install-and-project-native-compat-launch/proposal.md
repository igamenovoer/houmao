## Why

The current pair workflow exposes `houmao-mgr install` and `houmao-mgr cao install` as if compatibility profiles were a native Houmao concept, but those commands only exist to preload CAO-shaped profile state for the session-backed launch path. That makes the public model inconsistent with Houmao's actual source of truth, which is the native agent-definition directory (`brains/`, `roles/`, `blueprints/`), and it forces demos and operators through a separate install step that native Houmao launch does not need.

We should remove that public install workflow and make session-backed launch consume native agent definitions directly. If the compatibility layer still needs a profile-shaped artifact for a provider, it should synthesize that artifact from native launch inputs at launch time. Brain-only launch must remain a first-class supported mode in that model: no role prompt means an intentionally empty system prompt, not an error or a degraded fallback.

## What Changes

- **BREAKING** Remove public `houmao-mgr install` and `houmao-mgr cao install` from the supported pair workflow and stop documenting compatibility profile install as an operator step.
- **BREAKING** Retire the public pair-owned install API surface that exists only to mutate compatibility profile state ahead of launch.
- Change session-backed `houmao-mgr launch` and `houmao-mgr cao launch` to resolve native agent-definition inputs directly from the effective agent-definition root instead of requiring a preinstalled compatibility profile name. In the first cut, that native selector resolution is recipe-based for the selected provider/tool lane; blueprint-by-name resolution is deferred.
- Define one launch-time native-to-compat projection model for the CAO-backed TUI path so provider adapters can consume synthesized compatibility artifacts without a separate install phase.
- Make brain-only launch an explicit supported contract for both native and compatibility-backed launch translation: absent role prompt means an empty system prompt.
- Update the interactive demo and related docs/specs to launch from tracked demo-owned or otherwise non-test native agent definitions instead of a tracked compatibility profile Markdown file.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-srv-ctrl-cao-compat`: Remove public install commands from the supported `houmao-mgr` contract and require session-backed launch to resolve native agent definitions instead of installed compatibility profiles.
- `houmao-cao-control-core`: Replace the compatibility profile install/store authority with launch-time projection from native agent definitions, including explicit brain-only empty-prompt behavior.
- `houmao-server`: Remove the public compatibility-profile install surface from the supported server contract.
- `houmao-server-agent-api`: Allow native launch contracts to represent brain-only launch without requiring a non-empty role prompt.
- `houmao-server-interactive-full-pipeline-demo`: Remove the install step from demo startup and require startup to resolve tracked native agent definitions directly.

## Impact

- Affected CLI modules under `src/houmao/srv_ctrl/commands/`, especially `install.py`, `launch.py`, `cao.py`, and native launch-resolution helpers.
- Affected server/control-core modules under `src/houmao/server/`, especially the compatibility control core, request models, and any public install routes or compatibility profile-store code.
- Affected native launch-resolution and runtime code under `src/houmao/agents/`, including a new shared launch-resolution seam used by both CLI and server layers.
- Affected demo assets, docs, tests, and OpenSpec contracts that currently encode `houmao-mgr install` or compatibility-profile Markdown as part of the supported workflow.
