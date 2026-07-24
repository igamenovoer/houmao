# Agent Loop Correctness Evaluator

Status: Design draft

## Purpose

Design the `houmao-agent-loop-evaluator` system skill. The skill teaches an operator agent who is authoring an agent-team execplan to design test cases for that execplan and to run those test cases in a bounded, isolated mode. The goal is to surface correctness problems before live execution instead of relying on manual user debugging.

The skill complements `$houmao-agent-loop-lite` and `$houmao-agent-loop-pro`. It consumes generated execplan artifacts under `<loop-dir>/execplan/` and produces a test-case manifest, a bounded-run report, and a verdict summary.

## Artifacts

- [Feature Requirement](feature-requirement.md)
- [Use Cases](usecases/README.md)
- [Design](design/README.md)
- [Agent Task](agent-task.md)

## Current Stage

The feature requirement baseline is captured. Use cases, interface contracts, and the skill design overview remain to be drafted.

## Related Context

- `.kimi-code/skills/houmao-agent-loop-lite/SKILL.md`: lite loop authoring and execution.
- `.kimi-code/skills/houmao-agent-loop-pro/SKILL.md`: pro loop authoring and execution with schema-rich contracts.
- `context/features/2026-07-11-houmao-dev-testing/`: prior work on Houmao development testing skills and evidence patterns.
- `src/houmao/agents/assets/system_skills/public/houmao-agent-loop-lite/`: lite skill source tree.
- `src/houmao/agents/assets/system_skills/public/houmao-agent-loop-pro/`: pro skill source tree.

## Open Questions

- Should the evaluator run the loop directly or replay recorded traces?
- What assertion language should test cases use?
- How should non-deterministic LLM outputs be handled in assertions?
- Should the skill generate tests automatically from contracts or only guide the operator to author them?
- Where do test-case manifests and reports live relative to `<loop-dir>`?
