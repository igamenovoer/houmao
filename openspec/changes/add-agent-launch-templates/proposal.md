## Why

Houmao currently has reusable source templates (`project easy specialist` and low-level `project agents presets`) and a runtime-only `LaunchPlan`, but it does not have a reusable user-owned launch template that captures how one source should be instantiated in a specific context. That gap makes repeatable launches awkward because operators must remember launch-time parameters such as instance name, workdir, auth override, mailbox binding, and other sticky launch choices.

The current low-level `preset` terminology also pulls double duty as both a declarative build recipe and an operator-facing launch entry, which makes the model harder to explain and leaves the missing middle layer ambiguous.

## What Changes

- Introduce a first-class reusable launch-template concept that binds one specialist or low-level recipe to durable launch-time defaults such as instance identity, workdir, auth override, mailbox config, prompt-mode override, env records, and backend or gateway posture.
- Add project-easy authoring and inspection flows for launch templates alongside existing specialist flows.
- Extend low-level project-local agent-definition semantics so operators can author launch templates against low-level recipes without hand-assembling repeated launch CLI input.
- Clarify low-level `preset` semantics as recipe-oriented source configuration, including a canonical public `recipe` term with compatibility aliases where needed.
- Update managed launch resolution so direct CLI launch follows explicit precedence across adapter defaults, recipe defaults, launch-template defaults, direct CLI overrides, and runtime-only mutations.

## Capabilities

### New Capabilities
- `agent-launch-templates`: reusable operator-owned launch templates that bind a specialist or low-level recipe to durable launch-time defaults without creating a live instance

### Modified Capabilities
- `houmao-mgr-project-easy-cli`: add easy-layer launch-template authoring, inspection, and template-backed instance launch semantics
- `houmao-mgr-project-agents-presets`: clarify low-level preset semantics as recipe-oriented configuration and define how low-level launch-template sources relate to named presets or recipes
- `houmao-mgr-agents-launch`: add template-aware managed launch resolution and explicit precedence between recipe defaults, launch-template defaults, and direct CLI overrides
- `project-config-catalog`: persist launch-template objects and their references to specialists or low-level recipe sources in the project-local catalog
- `brain-launch-runtime`: preserve launch-template-derived build and launch inputs as part of the supported build-to-runtime resolution contract

## Impact

- Affected code: `src/houmao/project/catalog.py`, `src/houmao/project/easy.py`, `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/agents/native_launch_resolver.py`, `src/houmao/agents/brain_builder.py`, `src/houmao/agents/realm_controller/launch_plan.py`
- Affected operator surfaces: `houmao-mgr project easy ...`, `houmao-mgr project agents presets ...`, `houmao-mgr agents launch ...`
- Affected storage/contracts: project-local catalog schema, compatibility projection under `.houmao/agents/`, build manifest provenance, launch selection terminology, and related docs/spec references
