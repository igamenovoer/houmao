## 1. Auto-Skill Assets

- [x] 1.1 Create `src/houmao/agents/assets/auto_skills/houmao-auto-system-prompt/SKILL.md` with trigger-only metadata and a `## Workflow` section.
- [x] 1.2 Add packaged auto-skill catalog/projection helpers that load from `houmao.agents.assets.auto_skills` without using the system-skill catalog.
- [x] 1.3 Reserve packaged auto-skill names and fail brain construction when project, selected, or private skills collide with `houmao-auto-system-prompt`.

## 2. System Prompt Retrieval CLI

- [x] 2.1 Add `houmao-mgr agents self system-prompt show --format text`.
- [x] 2.2 Resolve the effective prompt through current-session managed-agent authority rather than direct manifest or memo path reads.
- [x] 2.3 Return clear errors for unmanaged sessions, explicit selectors under `agents self`, and missing effective prompt state.

## 3. Launch Policy and Role Injection

- [x] 3.1 Extend launch-policy capability metadata to distinguish native system-prompt support, provider skill support, and startup-visible skill metadata support.
- [x] 3.2 Add an `auto_skill_system_prompt` role injection method and select it for Kimi strategies that lack native system-prompt support but expose startup-visible skill metadata.
- [x] 3.3 Prefer native role injection when native provider support exists and fail clearly when neither native prompt nor startup-visible skill metadata support exists.
- [x] 3.4 Stop sending chat bootstrap messages for launches that select `auto_skill_system_prompt`.

## 4. Brain Construction and Runtime Provenance

- [x] 4.1 Project required auto skills into the provider-visible managed skill root before provider start.
- [x] 4.2 Ensure auto-skill projection updates Kimi skill discovery setup, including `extra_skill_dirs`, even when no other skills are projected.
- [x] 4.3 Keep auto-skill projection independent from managed system-skill policy, including disabled and exact-replacement system-skill selections.
- [x] 4.4 Record auto-skill provenance with selected names, reason, projected relative directories, destination root, and prompt reference/hash while avoiding false `applied` claims.

## 5. Tests and Validation

- [x] 5.1 Add unit tests for auto-skill catalog loading, projection, name collision failures, and system-skill-policy independence.
- [x] 5.2 Add unit tests for `agents self system-prompt show --format text` success and failure paths.
- [x] 5.3 Add launch-policy tests for native, Kimi auto-skill fallback, and unsupported fallback selection.
- [x] 5.4 Add runtime tests proving auto-skill injection avoids chat bootstrap and still exposes prompt retrieval.
- [x] 5.5 Add Kimi-specific tests proving `extra_skill_dirs` is configured when only `houmao-auto-system-prompt` is projected.
- [x] 5.6 Run `pixi run test` and targeted runtime tests that cover Kimi managed launch planning.
