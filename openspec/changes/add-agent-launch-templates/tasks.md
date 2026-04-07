## 1. Catalog And Projection

- [ ] 1.1 Add project-catalog data models and persistence for launch templates, including specialist-or-recipe source references and managed prompt-overlay content references.
- [ ] 1.2 Materialize catalog-backed launch templates into `.houmao/agents/launch-templates/` while keeping existing preset projection behavior unchanged.
- [ ] 1.3 Add template inspection payloads that report source identity, template-owned launch defaults, and secret-free prompt-overlay metadata.

## 2. Low-Level Recipe Surfaces

- [ ] 2.1 Add canonical `houmao-mgr project agents recipes <verb>` command surfaces and keep `project agents presets <verb>` as compatibility aliases for the same resources.
- [ ] 2.2 Update low-level recipe load, get, list, and set flows so operator-facing help and structured output use recipe terminology while preserving `.houmao/agents/presets/` storage.
- [ ] 2.3 Add low-level launch-template administration and resolution helpers that can target named recipes through one shared project-local source model.

## 3. Easy Launch Templates

- [ ] 3.1 Implement `houmao-mgr project easy template create`, `list`, `get`, and `remove` against the catalog-backed template model.
- [ ] 3.2 Extend `houmao-mgr project easy instance launch` to accept `--template`, apply template defaults, enforce selector conflicts, and preserve existing specialist and Gemini launch rules.
- [ ] 3.3 Extend easy instance inspection so `list` and `get` report originating launch-template identity when runtime provenance is available.

## 4. Managed Launch Resolution

- [ ] 4.1 Extend `houmao-mgr agents launch` to resolve `--template`, derive the underlying specialist-or-recipe source, and apply template defaults before direct CLI overrides.
- [ ] 4.2 Plumb launch-template defaults through build inputs, launch planning, and runtime manifests for auth selection, env records, mailbox config, managed-agent identity, and secret-free template provenance.
- [ ] 4.3 Compose launch-template prompt overlays into the effective role prompt before backend-specific role injection and keep resumed turns from replaying overlay bootstrap separately.

## 5. Tests And Documentation

- [ ] 5.1 Add unit and integration coverage for catalog persistence, compatibility projection, recipe alias surfaces, and easy-template CRUD flows.
- [ ] 5.2 Add launch-flow coverage for template-backed easy launches, low-level `agents launch --template`, precedence rules, mailbox handling, and runtime provenance reporting.
- [ ] 5.3 Update operator docs and conceptual references to distinguish recipes, launch templates, runtime `LaunchPlan`, and live instances, including the canonical recipe terminology and preset compatibility note.
