## Why

Houmao intentionally exposes two operator lanes for agent work:

- an easy lane that defaults common choices and hides low-level detail
- an explicit lane that exposes more of the launch contract so behavior is not hidden

That split already exists for source definitions through `project easy specialist ...` versus low-level `project agents presets ...` / `recipes ...`.

What is still missing is the same split for reusable birth-time launch configuration. Operators can define what an agent is, but they still have to remember how to launch it in one recurring context: managed-agent name, working directory, auth override, mailbox binding, prompt overlay, and similar launch-time decisions.

The previous launch-template framing also left the user-facing naming muddy. `template` is too generic, and one shared noun on both easy and non-easy surfaces would blur the intentional contract difference between those lanes.

## What Changes

- Introduce a shared catalog-backed launch-profile semantic model for reusable birth-time launch configuration.
- Add an easy specialist-backed `project easy profile ...` surface that exposes an opinionated subset of launch-profile authoring for common use cases.
- Add an explicit recipe-backed `project agents launch-profiles ...` surface that exposes the fuller low-level birth-time launch contract.
- Keep low-level source terminology moving toward canonical `recipe` naming while preserving `presets` compatibility aliases where needed.
- Update managed launch resolution so easy profiles and explicit launch profiles both resolve through one precedence model across source defaults, profile defaults, direct CLI overrides, and runtime-only mutations.

## Capabilities

### New Capabilities
- `agent-launch-profiles`: reusable operator-owned birth-time launch definitions with shared persistence, precedence, and projection semantics
- `houmao-mgr-project-agents-launch-profiles`: explicit low-level recipe-backed launch-profile authoring and inspection

### Modified Capabilities
- `houmao-mgr-project-easy-cli`: add easy `profile` authoring, inspection, and profile-backed instance launch semantics
- `houmao-mgr-project-agents-presets`: clarify low-level preset semantics as recipe-oriented source configuration and define recipe ownership relative to launch profiles
- `houmao-mgr-agents-launch`: add explicit launch-profile-backed managed launch resolution and provenance reporting
- `project-config-catalog`: persist shared launch-profile objects and their specialist-backed or recipe-backed provenance
- `brain-launch-runtime`: preserve launch-profile-derived build and launch inputs as part of the supported build-to-runtime resolution contract

## Impact

- Affected code: `src/houmao/project/catalog.py`, `src/houmao/project/easy.py`, `src/houmao/srv_ctrl/commands/project.py`, `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/agents/native_launch_resolver.py`, `src/houmao/agents/brain_builder.py`, `src/houmao/agents/realm_controller/launch_plan.py`
- Affected operator surfaces: `houmao-mgr project easy ...`, `houmao-mgr project agents recipes ...`, `houmao-mgr project agents launch-profiles ...`, `houmao-mgr agents launch ...`
- Affected storage/contracts: project-local catalog schema, compatibility projection under `.houmao/agents/launch-profiles/`, build manifest provenance, launch selection terminology, and related docs/spec references
