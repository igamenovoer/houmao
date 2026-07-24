# Agent Task

## Objective

Implement the `houmao-agent-loop-evaluator` skill that teaches an operator agent to design and run correctness tests for a generated agent-loop execplan.

## Required Use Cases

- TBD: design test cases from execplan contracts.
- TBD: run bounded evaluation and produce a verdict report.

## Design References

- [Feature Requirement](feature-requirement.md)
- [Design](design/README.md)

## Implementation Instructions

- TBD after use cases and interfaces are designed.

## Verification

- TBD

## Required Evidence

Evidence packs should be written to a local, ignored output root and should not be committed unless explicitly requested.

Each evidence pack should include:

- `input/`: sample execplan package and test-case manifest.
- `output/`: evaluation report and captured run artifacts.
- `README.md`: what was run and how to inspect the results.

## Out Of Scope

- TBD

## Open Questions

- See the open questions in [Feature Requirement](feature-requirement.md).
