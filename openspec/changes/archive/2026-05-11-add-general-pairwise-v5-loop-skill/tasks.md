## 1. Packaged Skill Surface

- [x] 1.1 Invoke `$skill-creator` before creating or substantially updating the packaged v5 skill assets, and apply its anatomy, progressive-disclosure, metadata, resource, and validation guidance.
- [x] 1.2 Add `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/` with top-level `SKILL.md` declaring the manual-only general v5 loop skill.
- [x] 1.3 Add `agents/openai.yaml` activation guidance that only routes to v5 on explicit `houmao-agent-loop-pairwise-v5` invocation or an explicitly named v5 operation.
- [x] 1.4 Register `houmao-agent-loop-pairwise-v5` in `src/houmao/agents/assets/system_skills/catalog.toml` with appropriate catalog description and install-set membership.
- [x] 1.5 Update system-skill inventory tests so v5 is discovered, installed, and reported with the existing pairwise skill family.

## 2. Authoring Subskills

- [x] 2.1 Add authoring subskill guidance for creating `<loop-dir>/intention/README.md` and `<loop-dir>/intention/loop-overview.md` from a user-provided intention.
- [x] 2.2 Add authoring subskill guidance for refining existing freeform intention Markdown without imposing a strict source schema.
- [x] 2.3 Add authoring subskill guidance for generating `<loop-dir>/execplan/` from the current intention source.
- [x] 2.4 Add authoring subskill guidance for validating generated execplan structure and generated-artifact markers.
- [x] 2.5 Add authoring subskill guidance for regenerating `execplan/` from edited intention source while treating `intention/` as the source of truth.

## 3. Execplan Contract Guidance

- [x] 3.1 Document the required v5 root layout: `<loop-dir>/intention/` plus generated `<loop-dir>/execplan/`.
- [x] 3.2 Document the generated execplan layout with `manifest.toml`, `specs/`, `skills/`, `agents/`, `harness/`, and `docs/`.
- [x] 3.3 Ensure v5 guidance explicitly excludes required `adrs/` discovery or validation in the initial workflow.
- [x] 3.4 Ensure guidance remains domain-neutral and does not encode reference-specific domain requirements.

## 4. Execution Subskills

- [x] 4.1 Add execution subskill guidance for preparing agents from a generated execplan while routing platform setup through maintained Houmao skills.
- [x] 4.2 Add execution subskill guidance for starting a generated v5 loop from `<loop-dir>/execplan/`.
- [x] 4.3 Add execution subskill guidance for read-only status inspection.
- [x] 4.4 Add execution subskill guidance for pause, resume, recovery, and stop flows.
- [x] 4.5 Ensure execution subskills route managed-agent launch, mailbox, gateway, memory, messaging, lifecycle, and inspection work through the existing owning Houmao skill surfaces.

## 5. Validation And Tests

- [x] 5.1 Add tests that the v5 top-level `SKILL.md` is manual-invocation-only and routes to authoring/execution subskills.
- [x] 5.2 Add tests or fixture checks that v5 authoring guidance requires `<loop-dir>` before creating files.
- [x] 5.3 Add tests or fixture checks that intention guidance requires `README.md` and `loop-overview.md` while allowing freeform additional Markdown.
- [x] 5.4 Add tests or fixture checks that execplan guidance names the required generated directories and `manifest.toml`.
- [x] 5.5 Run `pixi run test tests/unit/srv_ctrl/test_system_skills_commands.py` or a narrower targeted unit test set covering packaged system skills.
- [x] 5.6 Run `openspec validate add-general-pairwise-v5-loop-skill --strict` and fix any artifact issues.
