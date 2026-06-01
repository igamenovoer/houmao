## Context

`houmao-agent-loop-pro` already uses the desired system-skill architecture: a concise `SKILL.md` router, operation-specific authoring and execution pages, shared reference pages, scaffold assets, and a scaffold script. That structure keeps activation and routing separate from detailed workflow guidance.

`houmao-agent-loop-lite` has the intended runtime semantics documented in specs and guides: Markdown contracts, typed Markdown templates, required generated skills, and direct SQLite state with no JSON schemas, no Jinja2, and no generated harness. Its packaged asset shape is the weak point: the guidance is flattened into one `SKILL.md`, so lite looks like a smaller ad hoc skill rather than a pro-shaped workflow with lighter generated artifacts.

This change aligns the lite package shape with pro while preserving lite's simpler generated material.

## Goals / Non-Goals

**Goals:**

- Make `houmao-agent-loop-lite/SKILL.md` an entrypoint/router with help, operations, route selection, root vocabulary, and global constraints.
- Split lite operation guidance into `subskills/authoring/`, `subskills/execution/`, and `subskills/reference/`.
- Add scaffold assets and a scaffold script for lite intention and execplan shells.
- Keep the lite generation pipeline pro-like but without `execplan-harness`.
- Preserve lite's generated artifact choices: Markdown specs, typed Markdown templates, generated skills, Markdown agent bindings, optional workspace/profile/notifier material, and direct SQLite state.
- Update tests so installation projects the new routed pages and guards against re-flattening.

**Non-Goals:**

- Do not add JSON Schema, Jinja2, generated harness commands, or generated docs to lite.
- Do not change maintained platform ownership for agent definitions, launch, gateway, mailbox, inspection, workspace preparation, or messaging.
- Do not implement a runtime CLI parser for lite operations; this is a system-skill workflow package.
- Do not preserve the single-page lite layout as a compatibility target.

## Decisions

1. Mirror pro's package topology, not pro's heavy artifact model.

   Lite should have the same human/operator workflow affordances as pro: routed pages, references, execution stages, and scaffold ownership. The simplification belongs inside generated artifacts, not in the skill package shape. The alternative was to keep lite in one page and add more sections, but that makes future authoring and execution changes hard to localize and contradicts the pro/lite relationship.

2. Keep lite operation names close to pro where they express the same lifecycle stage.

   The router should support authoring operations such as `init`, `clarify-intent`, `clarify-execplan`, `execplan-fast-forward`, `execplan-specs-process`, `execplan-specs-contract`, `execplan-skills`, `execplan-agent-bindings`, `execplan-finalize`, `validate-execplan`, and `update-execplan`, plus execution operations such as `prepare-agents`, `prepare-workspace`, `validate-loop`, `launch-agents`, `start`, `status`, `pause`, `resume`, `recover`, and `stop`. Existing lite-friendly names such as `clarify`, `generate-skills`, and `validate` can be described as aliases only if the implementation keeps their meaning unambiguous.

3. Use Markdown contracts as first-class generated authorities.

   Lite should still generate process-first and contract-stage material, but those contracts are Markdown files under `execplan/specs/` instead of TOML registries plus schemas. Markdown tables, required headings, and explicit placeholder conventions are the structured substrate. `execplan/specs/state/schema.sql` remains the SQLite schema authority when durable state is needed.

4. Omit the harness stage entirely.

   The lite fast-forward pipeline should be:

   ```text
   execplan-specs-process
     -> execplan-specs-contract
         -> execplan-skills
             -> execplan-agent-bindings
                 -> execplan-finalize
   ```

   Generated skills operate directly against Markdown contracts, Markdown templates, and SQLite. Validation checks these direct contracts instead of looking for harness commands.

5. Keep scaffold-owned starter material separate from routed page prose.

   Lite should gain `assets/scaffolds/` and `scripts/scaffold.py` so starter README, manifest, specs, template, state, skills, and agents shells are owned in assets rather than copied into operation pages. This mirrors the pro maintenance pattern and makes tests able to assert the package shape.

## Risks / Trade-offs

- [Risk] The lite package becomes larger and may feel less "lite" at first glance. → Mitigation: keep page content concise and repeatedly state that lite is lightweight in generated artifacts, not in lifecycle discipline.
- [Risk] Pro-only concepts may leak into lite while copying structure. → Mitigation: add tests and spec language that forbid JSON schemas, Jinja2 renderers, generated harness directories, and generated docs.
- [Risk] Old operation names may confuse users if removed abruptly. → Mitigation: either document clear aliases or intentionally mark the new pro-like operation names as the supported surface in docs and tests.
- [Risk] Direct SQLite state can be underspecified without harness helpers. → Mitigation: make `direct-sqlite-state.md`, `execplan/specs/state/README.md`, and generated skills carry explicit initialization, transaction, query, mutation, validation, and recovery rules.
