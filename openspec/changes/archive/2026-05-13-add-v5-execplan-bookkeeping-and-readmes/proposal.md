## Why

Generated loop packages contain many directories with different artifact types, and later agents need quick local orientation without reading every contract file. Short `README.md` files in generated artifact directories make the package easier to inspect while avoiding duplicated authority.

Generated loops also need a clear bookkeeping model. Skill-invoked agents must know what belongs in runtime state, what remains in mail or artifacts, how to define state schemas, and how to expose safe harness commands for state initialization, mutation, validation, and query.

## What Changes

- Require generated artifact directories to include a concise `README.md`.
- Keep each README limited to:
  - `Purpose`: why the directory exists;
  - `Contents`: what files or child directories are present.
- Update v5 authoring guidance so every generation stage emits or updates README files for the directories it creates or materially populates.
- Update scaffold templates so known shell directories start with README files where practical.
- Update validation guidance to check README presence and reject README files that duplicate contracts or become a source of authority.
- Introduce generic bookkeeping principles for goal-oriented loops:
  - bookkeeping is control-plane state;
  - mail remains communication authority;
  - state stores compact facts, refs, ownership, decisions, evidence links, and transition audit;
  - rich narrative stays in mail, docs, and artifacts.
- Define expected generated state contract artifacts under `execplan/specs/state/`.
- Clarify generated state/bookkeeping defaults: prefer sqlite when the SQL schema is clearly defined; allow JSONL plus schema as the secondary option.
- Teach generated harnesses to initialize, validate, query, and apply state records through schema-checked commands.
- Require generated TOML contract records that the harness exposes to include `description` fields, teach harness `--explain` output to print those descriptions, and require human-readable comments above generated TOML sections.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-agent-loop-pairwise-v5-skill`: Generated execplan artifact directories gain concise README orientation requirements, generated bookkeeping principles, TOML readability and description guidance, state schema guidance, and harness integration expectations.

## Impact

- Affected skill assets: `src/houmao/agents/assets/system_skills/houmao-agent-loop-pairwise-v5/`
- Affected authoring pages: scaffold generation, process specs, contract specs, harness, skills, agent bindings, finalization, and validation.
- Affected generated execplans: new or updated `README.md` files under generated artifact directories.
- Affected generated state artifacts: `specs/state/` contracts, sqlite-backed bookkeeping when schemas are clear, JSONL-plus-schema as an alternate representation, and harness commands that use those contracts.
- Affected generated TOML artifacts: human-readable section comments plus structured `description` fields for harness-explainable contract entries.
- No runtime behavior change; README files are human orientation only.
