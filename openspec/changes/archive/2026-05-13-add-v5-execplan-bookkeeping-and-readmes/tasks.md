## 1. Scaffold Templates

- [x] 1.1 Add or update scaffold README templates for known generated execplan shell directories.
- [x] 1.2 Ensure scaffold-generated README templates use only `Purpose` and `Contents` sections.

## 2. Authoring Guidance

- [x] 2.1 Update top-level v5 generated-contract guidance to require concise README files for emitted generated artifact directories.
- [x] 2.2 Update process and contract generation subskills to create or update README files for emitted `specs/` directories.
- [x] 2.3 Update state-generation guidance with generic bookkeeping principles: control-plane state, mail refs, compact facts, ownership, transitions, evidence, operator intent, and valid state space.
- [x] 2.4 Update state-generation guidance so generated bookkeeping defaults to sqlite when a clear SQL schema exists, with JSONL plus schema as the alternate option.
- [x] 2.5 Update state contract guidance to emit `execplan/specs/state/README.md`, `state-overview.md`, backend schema files, seed data when needed, and invariants when validation needs them.
- [x] 2.6 Update generated TOML guidance so generated sections have human-readable comments and agent-facing or harness-facing contract records include concise `description` fields.
- [x] 2.7 Update harness generation guidance to create or update README files for emitted `harness/` directories.
- [x] 2.8 Update harness generation guidance to integrate state through init, validate, query, record-validate, and record-apply commands.
- [x] 2.9 Update harness generation guidance so `--explain` prints TOML `description` fields and JSON Schema descriptions with stable source keys.
- [x] 2.10 Update skills generation guidance to create or update `execplan/skills/README.md` and generated skill directory README files when extra generated files exist.
- [x] 2.11 Update agent-binding generation guidance to create or update README files for emitted `agents/` directories.
- [x] 2.12 Update finalization guidance to fill README gaps and keep README files limited to purpose and contents.

## 3. Validation And Design Docs

- [x] 3.1 Update `validate-execplan` to check README presence for emitted generated artifact directories.
- [x] 3.2 Update validation guidance to accept simple generated skill directories without `README.md` when `SKILL.md` is the only required orientation file.
- [x] 3.3 Update validation guidance to reject unstructured ad hoc bookkeeping state when sqlite or JSONL plus schema is feasible.
- [x] 3.4 Update validation guidance to check generated state contract coherence: state overview, schema artifacts, invariants, and harness command coverage.
- [x] 3.5 Update validation guidance to report missing TOML section comments and missing `description` fields for generated records or sections exposed through harness `--explain`.
- [x] 3.6 Update developer design docs and reference patterns to document the simple README convention, bookkeeping principles, TOML comments, TOML descriptions, generated state backend defaults, and harness integration.

## 4. Verification

- [x] 4.1 Validate the updated v5 skill package.
- [x] 4.2 Run `git diff --check`.
- [x] 4.3 Confirm `openspec instructions apply --change add-v5-execplan-bookkeeping-and-readmes --json` reports the change apply-ready.
