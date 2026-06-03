## Context

`houmao-mgr internals command-templates` was created to keep agents from hand-authoring stale CLI command skeletons. That worked for argv rendering, but the same surface is now doing too much for project configuration authoring: `show` emits full option schemas, `render` returns omitted-field metadata, and packaged skills often instruct agents to call both before creating ordinary specialists or profiles.

The project subsystem already has a semantic source of truth in the SQLite-backed project catalog and typed catalog entries such as specialists and launch profiles. It also already renders compatibility YAML projections for persisted objects. The config-draft refactor should lean on those domain shapes instead of creating a more elaborate command-template registry.

## Goals / Non-Goals

**Goals:**
- Provide a concise agent-facing internal CLI for generating concrete YAML config drafts from small intents.
- Keep draft generation code-first and model-driven, with fixed lane/source/default values encoded in Python functions and typed models.
- Cover the high-token pre-launch authoring flows first: easy specialists, specialist-backed easy profiles, and recipe-backed raw launch profiles.
- Update packaged skills so agents use config drafts for config-document authoring and command templates only when they truly need argv rendering.
- Preserve existing command-template behavior unless a targeted test or skill migration requires a compatibility-safe adjustment.

**Non-Goals:**
- Do not make YAML files the runtime source of truth for the project catalog.
- Do not introduce Jinja2, JSON Schema, a placeholder language, or a general dynamic template DSL.
- Do not remove `internals command-templates` in this change.
- Do not add a broad config import/apply engine unless a later change explicitly scopes it.
- Do not move credential, gateway, mailbox, or live lifecycle command authoring wholesale onto config drafts; those surfaces remain command-oriented unless they gain real config-document shapes.

## Decisions

### Add `houmao-mgr internals config-drafts`

Create a sibling internal command family:

```text
houmao-mgr internals config-drafts list
houmao-mgr internals config-drafts generate --id <draft-id> --intent '<json>'
```

Initial draft ids should be stable and domain-oriented:

```text
project.easy.specialist
project.easy.profile
project.agents.launch-profile
```

`list` should return a small inventory: id, description, config kind, and required intent keys. It should not return full field catalogs, omitted-field semantics, CLI options, or conflicts.

`generate` should accept a JSON object with a `fields` mapping, validate only the required and supported inputs for that draft id, and emit raw YAML on success. On blockers, it should fail clearly with focused missing/unsupported/conflicting input messages. If JSON output support is needed for tests or machines, keep it compact and include only draft id, blockers, and the rendered YAML string; do not include a schema catalog.

Alternative considered: add a compact mode to `command-templates render`. That would reduce output size, but it would keep config authoring coupled to the CLI option grammar rather than the project domain model.

### Implement drafts as concrete generators, not dynamic templates

Add a small package such as `houmao.srv_ctrl.config_drafts` with:

```text
models.py      typed draft result/blocker/intents
registry.py    draft id registry
rendering.py   YAML serialization and intent loading
families/
  project_agent_config.py
```

Each draft generator should be an ordinary Python function that returns a concrete mapping or typed draft object. For example, the easy-profile generator should always set `profile_lane: easy_profile` and `source.kind: specialist`; callers provide only values such as `name`, `specialist`, and explicit defaults they want represented.

The generated YAML should contain only meaningful config values. It should not list unsupported options, absent optional fields, clear flags, conflict descriptions, or generic omit prose.

Alternative considered: store draft YAML templates as package assets with placeholders. That would be concise initially, but it would drift from the typed catalog model and reintroduce a second config language.

### Reuse project-domain rendering shapes where possible

The raw launch-profile draft should align with the existing launch-profile YAML projection shape: `profile_lane`, `source`, and `defaults`. If the existing private projection renderer is close but too coupled to persisted catalog entries, extract a small shared payload builder so both persisted projections and internal drafts produce the same semantic structure.

The easy-profile draft can use the same launch-profile YAML shape with `profile_lane: easy_profile` and `source.kind: specialist`.

The specialist draft may need a small high-level semantic YAML shape because persisted specialist state spans a role prompt, credential/setup selection, launch metadata, skills, mailbox policy, and compatibility preset projection. Keep that shape explicit and small; do not force it through the launch-profile projection format if the semantics differ.

Alternative considered: make config drafts produce existing CLI intent JSON. That keeps command execution simple, but it does not give agents the readable YAML config document the new workflow is trying to provide.

### Treat generated drafts as authoring aids, not catalog source of truth

The first implementation should generate draft documents for agents and humans to inspect, report, or use while constructing subsequent maintained commands. It should not teach Houmao to load arbitrary generated YAML into the catalog. Existing create/set commands remain the mutation boundary until a separate config import/apply design exists.

This keeps the change low-risk: config drafts reduce token load and clarify semantics without changing storage, migration, or persistence guarantees.

Alternative considered: add `project config apply --file draft.yaml` now. That may be useful later, but it expands this refactor into a new mutation API and requires a stronger validation/migration contract.

### Migrate packaged skills at the workflow boundary

Update `houmao-agent-definition` so:

- `specialists`, `profiles`, `raw-profiles`, and profile preparation inside `create-agent-fast-forward` use `internals config-drafts generate` to obtain the concise YAML authoring shape.
- `roles`, `recipes`, and live launch-command printing may continue using `internals command-templates render` until they gain config-draft shapes or a stronger reason to move.
- Credential material command authoring remains delegated to `houmao-credential-mgr` or credential command templates because credential CRUD is still command-shaped, not profile-document-shaped.

Update `houmao-memory-mgr` so memo-seed guidance for profile documents points to the relevant profile config draft rather than profile command-template fields.

Alternative considered: update every system skill that mentions command templates in one sweep. That would be noisy and would move command-oriented workflows onto a config abstraction they do not yet need.

## Risks / Trade-offs

- Draft YAML may be mistaken for an importable source-of-truth file -> Label outputs and skill guidance as drafts unless/until an apply/import workflow exists.
- Draft shape may drift from persisted projection shape -> Share payload builders with project catalog projection code where the semantics are the same.
- Internal command family proliferation could confuse agents -> Keep names domain-specific (`config-drafts` versus `command-templates`) and update skills with a simple rule: config documents use drafts, executable commands use command templates.
- Raw YAML output bypasses generic JSON rendering -> Provide focused tests for plain YAML output and compact JSON/blocker behavior if JSON mode is supported.
- Specialist config spans multiple persisted objects -> Keep the specialist draft high-level and semantic rather than pretending it is one existing projection file.

## Migration Plan

1. Add config-draft models, registry, YAML generation, and `internals config-drafts list|generate`.
2. Add draft generators for easy specialist, easy profile, and raw launch profile.
3. Add unit and CLI-shape tests that assert concise output and absence of command-template schema keys such as `fields`, `omitted_fields`, and `target_argv`.
4. Update `houmao-agent-definition` and `houmao-memory-mgr` packaged skill guidance to use config drafts for profile/specialist config authoring.
5. Keep command-template tests green and add regression coverage that command-template exports remain available for command-oriented workflows.

## Open Questions

- Should `generate` always emit raw YAML, or should `--print-json` return a compact wrapper containing the YAML string for easier test parsing?
- Should the first specialist draft include prompt text inline, prompt-file references, or both depending on supplied intent?
- Should roles and recipes receive config-draft ids in this change, or should they remain command-template-backed until their desired YAML shape is clarified?
