## 1. Skill Guidance

- [x] 1.1 Add top-level communication defaults to `houmao-agent-loop-pairwise-v5/SKILL.md`, including Houmao mail as the default cross-agent communication mechanism and maintained Houmao skill ownership for mail mechanics.
- [x] 1.2 Update `agents/openai.yaml` so the packaged prompt mentions mail defaults and delegation without adding standalone version-language to the skill body.
- [x] 1.3 Update `subskills/authoring/clarify-intent.md` so clarification treats Houmao mail and maintained mail-skill delegation as defaults, then asks only loop-specific communication questions.

## 2. Execplan Generation And Validation

- [x] 2.1 Update `subskills/authoring/generate-execplan.md` so mail-driven loops generate communication semantics under `specs/comms/`, generated role skills, agent bindings, and harness surfaces while routing actual mailbox actions to maintained Houmao skills.
- [x] 2.2 Add explicit generated comms package guidance for `specs/comms/templates.toml`, JSON schemas, Markdown renderers, and a generated communication overview.
- [x] 2.3 Add default payload-envelope and rendered-mail-shape guidance, including `schema_id`, `schema_version`, `payload_id`, `kind`, `run_id`, `plan_revision`, exchange or handoff id, `context`, `houmao-email-metadata`, and explicit reply requests.
- [x] 2.4 Add explicit generated mail-family guidance for structured payloads, schema validation, Markdown rendering, request-to-reply schema links, and Houmao mail send/reply.
- [x] 2.5 Add generated payload lifecycle guidance for harness `email schema|validate|render|apply|query`, while keeping mailbox delivery outside the harness.
- [x] 2.6 Add generated mail-received event-skill guidance, including schema-id triggers, bounded processing, reply behavior, archive-after-success behavior, and separation from on-tick aggregation or scheduling.
- [x] 2.7 Update `subskills/authoring/validate-execplan.md` so validation checks for mail default delegation, template registry wiring, schema/render communication contracts, payload lifecycle posture, and generated role-skill trigger boundaries when a loop is mail-driven.
- [x] 2.8 Update execution guidance if needed so agent preparation binds required maintained Houmao mail skills when generated agent bindings require mail participation.

## 3. Developer Notes And Tests

- [x] 3.1 Update `dev/design/` notes to document the communication-default pattern and explain the boundary between generated loop communication semantics and Houmao platform mail mechanics.
- [x] 3.2 Document which reference-plan mail patterns are defaults and which are intentionally not defaults, such as exact topology, domain template names, evidence fields, and required SQLite backend.
- [x] 3.3 Add or update unit tests in `tests/unit/agents/test_system_skills.py` to assert the packaged skill includes mail defaults, maintained Houmao mail skill routing, clarify defaults, generated comms registry guidance, common payload envelope guidance, rendered metadata guidance, payload lifecycle guidance, and mail-received event-skill guidance.
- [x] 3.4 Run `pixi run pytest tests/unit/agents/test_system_skills.py -q` and fix any failures.
- [x] 3.5 Verify no standalone `v5`/`V5` wording is introduced in the skill body outside the actual skill name/path.
