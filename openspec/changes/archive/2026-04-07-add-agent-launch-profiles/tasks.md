## 1. Catalog And Projection

- [x] 1.1 Add project-catalog data models and persistence for shared launch profiles, including source-lane provenance for specialist-backed easy profiles and recipe-backed explicit launch profiles.
- [x] 1.2 Materialize catalog-backed launch profiles into `.houmao/agents/launch-profiles/` while keeping existing preset projection behavior unchanged.
- [x] 1.3 Add launch-profile inspection payloads that report source identity, profile lane, profile-owned launch defaults, and secret-free prompt-overlay metadata.

## 2. Low-Level Recipe And Launch-Profile Surfaces

- [x] 2.1 Add canonical `houmao-mgr project agents recipes <verb>` command surfaces and keep `project agents presets <verb>` as compatibility aliases for the same resources.
- [x] 2.2 Add `houmao-mgr project agents launch-profiles <verb>` for recipe-backed explicit birth-time launch-profile authoring and inspection.
- [x] 2.3 Update low-level recipe and launch-profile output so operator-facing help and structured output use recipe and launch-profile terminology while preserving `.houmao/agents/presets/` storage.

## 3. Easy Specialist Profiles

- [x] 3.1 Implement `houmao-mgr project easy profile create`, `list`, `get`, and `remove` as the specialist-backed easy authoring surface over shared launch-profile records.
- [x] 3.2 Extend `houmao-mgr project easy instance launch` to accept `--profile`, apply easy-profile defaults, enforce selector conflicts, and preserve existing specialist and Gemini launch rules.
- [x] 3.3 Extend easy instance inspection so `list` and `get` report originating easy-profile identity when runtime provenance is available.

## 4. Managed Launch Resolution

- [x] 4.1 Extend `houmao-mgr agents launch` to resolve `--launch-profile`, derive the underlying recipe source, and apply launch-profile defaults before direct CLI overrides.
- [x] 4.2 Plumb launch-profile defaults through build inputs, launch planning, and runtime manifests for auth selection, env records, mailbox config, managed-agent identity, and secret-free provenance.
- [x] 4.3 Compose launch-profile prompt overlays into the effective role prompt before backend-specific role injection and keep resumed turns from replaying overlay bootstrap separately.

## 5. Tests And Documentation

- [x] 5.1 Add unit and integration coverage for catalog persistence, compatibility projection, recipe alias surfaces, easy-profile CRUD flows, and explicit launch-profile CRUD flows.
- [x] 5.2 Add launch-flow coverage for `project easy instance launch --profile`, `agents launch --launch-profile`, precedence rules, mailbox handling, and runtime provenance reporting.
- [x] 5.3 Update operator docs and conceptual references to distinguish specialists, recipes, easy profiles, explicit launch profiles, runtime `LaunchPlan`, and live instances.
