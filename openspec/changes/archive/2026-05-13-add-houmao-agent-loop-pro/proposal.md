## Why

The current pairwise-v5 skill has the stronger generated-execplan authoring pipeline, while the older generic loop skill has useful typed graph concepts but still assumes a root owner. A new `houmao-agent-loop-pro` skill should preserve the v5 scaffold/execplan workflow while supporting both local-close pairwise trees and true generic directed loops where predecessor-context handling is an explicit execplan design concern.

## What Changes

- Add a new `houmao-agent-loop-pro` system skill copied from the current pairwise-v5 skill as the baseline.
- Rename skill metadata and user-facing body text so the new skill is not presented as a v5 or pairwise-only workflow.
- Add explicit topology modes:
  - `pairwise-tree`: all execution edges are local-close upstream/downstream handoffs, and operational subgraphs must be trees or forests.
  - `generic-graph`: arbitrary directed graph loops such as `A -> B -> C -> A` are allowed when communication, state, context-selection, and termination choices are explicit enough for the task.
- Teach the new skill to normalize non-tree pairwise intent into tree-shaped execution by selecting an existing participant as the relay/cycle breaker instead of creating a new participant.
- Add generated execplan contract guidance for topology, task-specific predecessor-context handling, result routing, graph validation, and cycle termination.
- Add generated communication guidance where templated mail families are identified by schema ids, rendered mail bodies include a parseable in-body metadata header, and generated on-event skills trigger from the detected schema id as the mail type.
- Extend clarification, process, contract, harness, generated-skill, and validation guidance so generated loops make the selected topology mode explicit.
- Keep old `houmao-agent-loop-pairwise-v5`, `houmao-agent-loop-generic`, and earlier pairwise skills unchanged.

## Capabilities

### New Capabilities

- `houmao-agent-loop-pro-skill`: Covers a generated-execplan Houmao loop authoring and execution skill that supports both pairwise-tree and generic-graph topology modes, including topology normalization, schema-typed mail events, task-specific predecessor-context handling, and loop readiness validation.

### Modified Capabilities

- None.

## Impact

- Adds a new system skill directory under `src/houmao/agents/assets/system_skills/houmao-agent-loop-pro/`.
- Reuses the existing v5 scaffold, subskill, template, script, and reference structure as the implementation baseline.
- Adds or revises new skill-local reference pages and authoring/execution pages for topology modes, graph contracts, schema-typed mail event routing, and task-specific communication context considerations.
- May add project-scope symlinks for Codex, Claude, and Copilot if the repository’s current system-skill exposure pattern requires them for new skills.
- No runtime Python API or Houmao core CLI behavior changes are expected.
