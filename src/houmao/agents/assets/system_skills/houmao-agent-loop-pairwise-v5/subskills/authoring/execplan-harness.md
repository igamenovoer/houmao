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

## Actions

1. Generate harness surfaces from generated contracts only.
2. Keep output intended for agents machine-readable where practical.
3. Use a common envelope with success status, command identity, run id when known, plan revision when known, data, diagnostics, and warnings, or document an equivalent.
4. Keep apply commands narrow and schema-validated.
5. Document any harness commands generated skills are expected to call.

## Downstream Effects

- Changes here invalidate generated skills, agent bindings that install harness helper skills, final docs, and final manifest.

## Constraints

- Do not make the harness own mailbox delivery, gateway discovery, managed-agent lifecycle, memory management, or workspace creation.
- Do not invent process or contract semantics that are absent from upstream specs.
