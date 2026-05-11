# Execplan Finalize

## Preconditions

- Upstream staged generation has emitted the authoritative generated artifacts for this revision.

## Inputs

Require:
- `<loop-dir>`;
- generated specs;
- generated harness surfaces when present;
- generated skills;
- generated agent bindings when present;
- any explicit omission notes from earlier stages.

## Outputs

Generate or update final package material:
- `execplan/README.md`;
- support docs under `execplan/docs/`;
- final `manifest.toml`;
- generated-source metadata;
- explicit omission notes;
- consistency notes for validation and operator review.

## Actions

1. Generate human docs from already generated authoritative artifacts.
2. Finalize `manifest.toml` after files exist so it indexes actual paths, artifact kinds, purposes, plan revision, and explicit omissions.
3. Ensure docs defer authority to `specs/`, `harness/`, generated skills, and agent bindings.
4. Record any intentionally skipped default layers.
5. Run or request `validate-execplan` after finalization.

## Downstream Effects

- This is the final generation stage. Changes here should not introduce new process, contract, harness, skill, or agent-binding semantics.

## Constraints

- Do not add new authoritative loop behavior only in docs.
- Do not leave stale manifest entries for files that were omitted or removed.
- Do not perform platform side effects.
