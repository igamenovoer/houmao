# Execplan Harness

## Preconditions

- Process and contract specs are current.
- The loop needs validation, dynamic lookup, rendering, query, completion, explanation, or controlled record application.

## Inputs

Require:
- `<loop-dir>`;
- generated process specs;
- generated contract specs that harness commands will read.

## Outputs

Generate or update `execplan/harness/` and harness-facing docs or references for:
- validation;
- objective and policy rendering;
- communication schema lookup, payload validation, rendering, lifecycle apply, and query;
- record schema lookup, validation, controlled apply, and query;
- state query and completion checks;
- structured explanation output when generated contracts provide explainable comments;
- structured machine-readable command envelopes.

Use this package shape when a harness is generated:

```text
<loop-dir>/execplan/harness/
  README.md
  commands.toml
  schemas/
    command-envelope.schema.json
  refs/
    <relative symlinks to package artifacts>
  bin/
    <command-wrapper>
  src/
    <implementation files>
```

`commands.toml` is the registry for generated harness commands. `bin/` and `src/` may be omitted only when the harness is a documented external or no-code surface, but the omission must be explicit. Do not leave command descriptions only as loose prose in `execplan/docs/`.

Path and schema rules:
- Treat `<loop-dir>/execplan/` as the generated loop-definition package.
- Harness config and command registries may refer to any generated artifact in that package by relative path.
- Prefer paths relative to `execplan/harness/`, such as `../specs/comms/templates.toml`, `../specs/comms/schemas/<message-family>.schema.json`, `../specs/collab/records/<record-family>.schema.json`, `../specs/state/state-model.toml`, `../specs/workspace/workspace.toml`, or `../agents/bindings.toml`.
- When harness scripts need stable local paths, create relative symlinks under `execplan/harness/refs/` that point to authoritative artifacts elsewhere in the package.
- Symlink targets must be relative, not absolute. For example, `execplan/harness/refs/comms-templates.toml` can point to `../../specs/comms/templates.toml`.
- If symlink creation is unavailable or blocked by filesystem permissions, do not copy the artifact. Have the harness script or `commands.toml` use the direct relative path to the authoritative artifact instead.
- Use `harness/schemas/` only for schemas owned by the harness itself, such as the command envelope schema.
- Do not copy communication, record, state, workspace, participant, or objective schemas into `harness/`; reference the authoritative files under `specs/` or other package directories.
- Avoid absolute paths for generated package references unless a generated contract explicitly defines an external runtime path.

## Actions

1. Generate harness surfaces from generated contracts only.
2. Keep output intended for agents machine-readable where practical.
3. Use a common envelope with success status, command identity, run id when known, plan revision when known, data, diagnostics, and warnings, or document an equivalent.
4. Make command definitions declare the artifact paths they read, validate, render, query, or apply, including whether each path is a harness-local relative symlink or a direct relative path to another package artifact.
5. Keep apply commands narrow and schema-validated.
6. Document any harness commands generated skills are expected to call.

## Downstream Effects

- Changes here invalidate generated skills, agent bindings that install harness helper skills, final docs, and final manifest.

## Constraints

- Do not make the harness own mailbox delivery, gateway discovery, managed-agent lifecycle, memory management, or workspace creation.
- Do not invent process or contract semantics that are absent from upstream specs.
