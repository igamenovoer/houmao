## Context

The current repo-local project overlay bootstraps `.houmao/agents/compatibility-profiles/` even though that subtree is optional, has no normal parser/build consumer, and is documented as specialized compatibility metadata rather than part of the main authoring workflow. In parallel, `project easy specialist create` currently forces two decisions that the underlying system does not always need:

- an explicit credential bundle name
- a non-empty system prompt source

That mismatch makes the higher-level project workflow more verbose than the canonical tree and runtime need. It also creates an inconsistency where brain-only launches already tolerate an empty system prompt, but ordinary role-backed specialist launches still assume a non-empty role prompt file.

## Goals / Non-Goals

**Goals:**

- Keep `project init` focused on the default project-overlay authoring roots.
- Make compatibility-profile root creation explicitly opt-in.
- Reduce `project easy specialist create` ceremony by deriving a stable default credential name.
- Support promptless specialists without inventing a parallel role model.
- Ensure native launch paths do not pass empty prompt arguments or bootstrap messages to provider CLIs.
- Preserve the canonical `.houmao/agents/` tree as the only authoritative build and launch input.

**Non-Goals:**

- Defining a full public contract for compatibility-profile contents or adding new compatibility workflows.
- Introducing a second specialist-specific prompt storage model separate from `roles/<role>/system-prompt.md`.
- Changing preset schema, provider selection, or auth-bundle projection layout.
- Implementing application code in this change artifact set.

## Decisions

### Decision 1: `project init` stops creating `compatibility-profiles/` by default and uses an explicit opt-in flag

`houmao-mgr project init` will continue to create the base overlay plus `skills/`, `roles/`, and `tools/`, but it will not create `.houmao/agents/compatibility-profiles/` unless the operator explicitly asks for it.

The proposed operator surface is a positive opt-in flag such as:

```text
houmao-mgr project init --with-compatibility-profiles
```

Rationale:

- The current design already treats `compatibility-profiles/` as optional metadata rather than a required project source root.
- Default bootstrap should create only the roots that the supported project authoring flow actively uses.
- A dedicated positive flag is clearer than creating the subtree speculatively and then explaining that most users can ignore it.

Alternatives considered:

- Keep creating the directory and treat it as harmless clutter: rejected because it weakens the stated project-init default of creating only the active authoring roots.
- Add a negative flag like `--without-compatibility-profiles`: rejected because the desired behavior is the new default, so an opt-out flag would encode the wrong operator posture.
- Add no flag at all and require manual directory creation: acceptable technically, but rejected because the user specifically wants an explicit enablement path.

### Decision 2: Specialist credential naming becomes derived-by-default but remains overridable

`project easy specialist create` will continue to accept `--credential <name>`, but when the flag is omitted it will derive the credential bundle name as `<specialist-name>-creds`.

Auth bundle behavior will be:

- if the target auth bundle already exists and no auth inputs are provided, reuse it
- if the target auth bundle already exists and auth inputs are provided, overwrite/update it through the existing `set`-style bundle path
- if the target auth bundle does not exist and auth inputs are provided, create it
- if the target auth bundle does not exist and no auth inputs are provided, fail clearly

Rationale:

- The current auth-bundle model already centers on stable named bundles under `tools/<tool>/auth/<name>/`.
- A deterministic derived default keeps the command short while preserving inspectable, explicit canonical outputs.
- Reuse-or-overwrite semantics match the current auth-bundle behavior and avoid inventing specialist-only credential persistence.

Alternatives considered:

- Auto-generate opaque credential names: rejected because it makes the canonical tree harder to inspect and reason about.
- Require `--credential` forever: rejected because it adds ceremony without adding meaningful information in the common case.
- Always overwrite the derived bundle even with no auth inputs: rejected because it would turn a no-input invocation into destructive behavior.

### Decision 3: Promptless specialists still compile to the canonical role prompt path as an empty file

Promptless specialists will still materialize:

```text
.houmao/agents/roles/<specialist>/system-prompt.md
```

but the file may be intentionally empty to mean “no system prompt.”

Specialist metadata will continue storing a concrete `system_prompt_path` rather than making that path optional.

Rationale:

- The current canonical tree treats `roles/<role>/system-prompt.md` as the stable role prompt location.
- Keeping the file path canonical avoids turning role inspection, role loading, project metadata, and launch resolution into two-shape logic.
- An empty file is sufficient to express the desired semantics without inventing a second representation for “no prompt.”

Alternatives considered:

- Make `system-prompt.md` optional or absent for promptless specialists: rejected because it creates broader contract churn across role loading and inspection.
- Store “no prompt” only in specialist metadata while omitting the role file: rejected because it would make `project easy` metadata a second source of truth.

### Decision 4: Empty role prompts remain valid launch inputs and suppress native prompt injection

Role loading and launch planning will treat an empty canonical role prompt as valid. The runtime will preserve the selected role identity, but native provider startup logic must suppress empty prompt injection:

- no empty `developer_instructions`
- no empty `--append-system-prompt`
- no bootstrap message generated from an empty prompt

Compatibility/profile-based paths may still carry an empty prompt string as role state, but they must not fail purely because the prompt is empty.

Rationale:

- The system already supports empty system prompt semantics for brain-only launch cases.
- Provider CLIs should not receive meaningless empty prompt flags just because a canonical role file exists.
- This keeps “promptless specialist” behavior aligned across project authoring and runtime execution.

Alternatives considered:

- Treat empty prompt as invalid outside brain-only launch: rejected because it preserves the current inconsistency and defeats the requested specialist behavior.
- Convert empty prompt into a boilerplate placeholder sentence: rejected because it changes semantics and still injects prompt content the operator did not ask for.

## Risks / Trade-offs

- [Risk] Adding an init flag for compatibility profiles could introduce help-surface clutter for a niche workflow. → Mitigation: keep the flag positive, explicit, and narrowly scoped to project bootstrap.
- [Risk] Empty prompt acceptance could unintentionally relax validation in places that relied on non-empty prompts for testing. → Mitigation: update loader, launch-plan, and backend tests to distinguish “file missing” from “file present but empty.”
- [Risk] Default credential naming could surprise operators who expected `default`. → Mitigation: document the derived naming rule clearly and preserve explicit `--credential` override behavior.
- [Risk] Reusing an existing derived auth bundle when no new auth inputs are supplied may hide stale credentials. → Mitigation: keep the behavior explicit in docs and surface the resolved credential name/path in command output.

## Migration Plan

1. Update the OpenSpec capability specs for project init, specialist creation, canonical role packages, runtime role injection, and getting-started docs.
2. Implement the project init flag/default change and adjust project-init tests.
3. Implement specialist-create default credential derivation and promptless specialist compilation.
4. Relax role loading for empty prompt files and update native launch builders to skip empty prompt injection.
5. Refresh docs and examples so `project init` output and `project easy specialist create` usage reflect the new defaults.

Rollback is straightforward because the change only affects local overlay generation, specialist authoring defaults, and runtime prompt application. Reverting the code change restores the prior stricter behavior without requiring persistent data migration.

## Open Questions

- Should low-level `project agents roles init/scaffold` also tolerate intentionally empty prompt content, or should this change stay scoped to specialist-generated roles first?
- Should `project init --with-compatibility-profiles` be the exact flag spelling, or does the existing CLI naming style suggest a better opt-in name?
