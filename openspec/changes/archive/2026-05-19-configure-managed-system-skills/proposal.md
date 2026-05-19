## Why

Managed agent homes currently receive a fixed Houmao-owned system-skill selection from the packaged `managed_launch_sets` catalog default. Operators can install different system-skill sets into external tool homes, but they cannot persistently choose which Houmao system skills a specialist-backed or launch-profile-backed managed agent receives at birth time.

This is now limiting because utility skills such as `houmao-utils-llm-wiki` are intentionally excluded from the managed `core` default while still being useful for selected managed agents.

## What Changes

- Add a first-class managed system-skill selection policy for managed launches.
- Allow `project easy specialist create/set` to persist a specialist-owned system-skill policy that is projected into the generated recipe launch payload.
- Allow easy profiles and explicit recipe-backed launch profiles to store profile-owned system-skill policy that can inherit, extend, replace, or disable the source policy for future launches.
- Resolve the effective managed system-skill selection during brain construction and install only that resolved selection into the managed tool home.
- Preserve secret-free provenance for the requested and resolved managed system-skill selection in build/runtime metadata.
- Validate requested system-skill set names and skill names against the packaged system-skill catalog before storing or building.
- Keep joined-session behavior unchanged: `agents join` continues to use the packaged `managed_join_sets` default and its existing skip flag.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-system-skill-installation`: managed launch auto-install can be overridden by an explicit source/profile system-skill policy while still using the packaged catalog and shared installer.
- `houmao-mgr-project-easy-cli`: easy specialists and easy profiles expose CLI options for stored managed system-skill policy.
- `agent-launch-profiles`: shared launch profiles store system-skill policy as reusable birth-time launch configuration with defined inheritance and mutation semantics.
- `houmao-mgr-project-agents-launch-profiles`: explicit recipe-backed launch profiles expose CLI options for stored managed system-skill policy.
- `brain-launch-runtime`: build and launch resolution applies the effective managed system-skill policy and records resolved provenance in generated manifests.

## Impact

- Affected code:
  - `src/houmao/agents/system_skills.py`
  - `src/houmao/agents/definition_parser.py`
  - `src/houmao/agents/brain_builder.py`
  - `src/houmao/srv_ctrl/commands/agents/core.py`
  - `src/houmao/srv_ctrl/commands/project_easy.py`
  - `src/houmao/srv_ctrl/commands/project_launch_profiles.py`
  - `src/houmao/srv_ctrl/commands/project_common.py`
  - `src/houmao/project/catalog.py`
- Affected data/contracts:
  - project catalog schema version and launch-profile compatibility projection
  - generated specialist recipe `launch` payload
  - build manifest/runtime launch provenance
- Affected docs:
  - system-skills overview and CLI reference
  - easy specialists guide
  - launch profiles guide
  - agent-definition/build/run references where they describe managed-home skill installation
- Tests should cover policy parsing, CLI storage/patch behavior, launch-profile inheritance/override semantics, catalog migration/defaults, build-home installation output, and manifest provenance.
