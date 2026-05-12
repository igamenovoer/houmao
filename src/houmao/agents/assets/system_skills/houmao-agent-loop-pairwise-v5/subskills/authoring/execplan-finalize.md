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
- execplan ADRs under `execplan/adrs/` when present;
- any explicit omission notes from earlier stages.

## Outputs

Generate or update final package material:
- `execplan/README.md`;
- missing generated artifact directory `README.md` files;
- support docs under `execplan/docs/`;
- final `manifest.toml`;
- generated-source metadata;
- explicit omission notes;
- consistency notes for validation and operator review.

Use this final support shape:

```text
<loop-dir>/execplan/
  README.md
  manifest.toml
  adrs/
    README.md
    0001-short-decision-slug.md
  docs/
    README.md
    artifact-index.md
    operator-guide.md
    runtime-model.md
    validation.md
```

Add narrower docs only when generated artifacts need them. Do not put authoritative contracts in `docs/`; docs summarize and link to `specs/`, `harness/`, `skills/`, and `agents/`.

## Actions

1. Use the packaged scaffold generator with the `execplan-finalize-docs` profile to materialize scaffold-owned `execplan/README.md` and named docs starters when they are missing or intentionally being refreshed.
2. Generate human docs from already generated authoritative artifacts.
3. Fill missing `README.md` files for emitted generated artifact directories.
4. Keep generated artifact directory README files limited to `Purpose` and `Contents`.
5. Finalize `manifest.toml` after files exist so it indexes actual paths, artifact kinds, purposes, plan revision, and explicit omissions.
6. Ensure docs defer authority to `specs/`, `harness/`, generated skills, and agent bindings.
7. For mail-driven loops, ensure docs summarize the notifier-prompt-driven runtime: mail notifier wakes agents, on-event skills process mail, optional on-tick skills run after mail when instructed, and agents finish the chat turn.
8. Index `execplan/adrs/` entries when present and summarize their affected artifacts without making docs the source authority.
9. Record any intentionally skipped default layers.
10. Run or request `validate-execplan` after finalization.

## Downstream Effects

- This is the final generation stage. Changes here should not introduce new process, contract, harness, skill, or agent-binding semantics.

## Constraints

- Do not add new authoritative loop behavior only in docs.
- Do not leave stale manifest entries for files that were omitted or removed.
- Do not perform platform side effects.
- Do not document in-chat waiting, sleeps, polling, or periodic tick workers as the runtime model.
