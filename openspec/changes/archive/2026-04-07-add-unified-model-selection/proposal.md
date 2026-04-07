## Why

Houmao currently treats model selection as a tool-specific implementation detail instead of a first-class launch input. Claude keeps the model in auth env, Codex typically keeps it in setup-owned `config.toml`, and Gemini does not expose a maintained Houmao model-selection surface at all, which means users cannot set one default model consistently across recipes, specialists, launch profiles, and one-off launches.

That same asymmetry also exists for reasoning depth. Codex has a first-class reasoning-effort field, Claude has a distinct effort concept plus separate thinking-budget controls, and Gemini routes reasoning-related behavior through model generation settings rather than through one scalar knob. Users should still be able to request a coarse reasoning level without learning each tool's native surface.

This makes the public mental model harder to understand and prevents launch profiles from covering a common birth-time choice. We need one secret-free semantic model-configuration surface that users can author once while Houmao handles projection into tool-specific runtime env, config files, or launch arguments.

## What Changes

- Introduce a first-class Houmao model-configuration capability that treats model choice and coarse reasoning level as reusable launch configuration rather than as auth-owned or setup-owned incidental state.
- Allow low-level recipes and high-level specialists to store a default model name and optional normalized reasoning level as part of their launch configuration.
- Allow both explicit launch profiles and easy profiles to store reusable model and reasoning overrides.
- Allow one-off launches from `houmao-mgr agents launch` and `houmao-mgr project easy instance launch` to override the effective model name and reasoning level at launch time.
- Define one shared precedence chain for effective model configuration across tool defaults, source defaults, launch-profile defaults, and direct launch-time overrides.
- Standardize coarse reasoning choice as a Houmao-owned normalized integer scale from `1` through `10`, where `1` always means the lowest reasoning Houmao will request for the resolved tool/model and `10` means the highest.
- Make the build/runtime pipeline project the resolved model configuration into the constructed runtime home using tool-specific mechanics, such as env injection, runtime config mutation, runtime settings mutation, or Houmao-owned generated config overlays, without requiring users to hand-author those tool-specific details.
- Add a Houmao-owned mapping policy layer, implemented in Python, that converts normalized reasoning levels plus runtime context such as tool, model name, and tool version into native config edits and projection actions.
- Document the mapping policy in user docs and concise CLI help, while leaving more detailed vendor-native tuning workflows to agent skills instead of expanding the core CLI indefinitely.
- Stop treating tool-specific model or reasoning storage in auth bundles or setup bundles as the primary user-facing authoring surface for new launch-owned workflows; those inputs become legacy fallback sources when present.

## Capabilities

### New Capabilities
- `agent-model-selection`: Define the tool-agnostic semantic model-configuration contract, including model name, normalized reasoning level, precedence rules, and runtime-home projection behavior for Claude, Codex, and Gemini.

### Modified Capabilities
- `agent-launch-profiles`: Extend the shared launch-profile model so reusable launch profiles can store default model configuration and contribute it during launch resolution.
- `houmao-mgr-project-agents-launch-profiles`: Extend the explicit launch-profile CLI so operators can author, inspect, and update stored model and reasoning overrides.
- `houmao-mgr-project-easy-cli`: Extend easy specialist, easy profile, and easy instance launch flows so they can author and override the shared model-configuration field.
- `houmao-mgr-project-agents-presets`: Extend low-level recipe authoring so named recipes can persist default model configuration in launch config.
- `houmao-mgr-agents-launch`: Extend direct launch so `agents launch` can accept one-off model and reasoning overrides and compose them with launch-profile and recipe defaults.
- `brain-launch-runtime`: Extend the build and runtime pipeline so resolved model configuration is preserved in manifests and projected into the runtime home through tool-specific supported surfaces and Houmao-owned mapping policy.

## Impact

- Affected code spans preset parsing, project catalog and launch-profile storage, easy specialist/profile authoring, direct launch resolution, brain building, and runtime-home projection.
- User-facing CLI surfaces will gain unified `--model` and `--reasoning-level` concepts on recipe/profile/launch paths, reducing reliance on tool-specific flags such as `--claude-model` or vendor-native reasoning settings.
- Runtime behavior will change for Claude, Codex, and Gemini managed homes because Houmao will actively project resolved model configuration into supported tool-native state before provider startup.
- Documentation and CLI help will need to explain that `reasoning-level` is a normalized Houmao scale whose exact native mapping depends on tool, model, and version.
