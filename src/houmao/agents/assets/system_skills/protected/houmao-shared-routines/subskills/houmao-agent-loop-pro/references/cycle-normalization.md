# Cycle Normalization

## Purpose

Use this page when tree-loop intent describes a non-tree closed loop.

## Tree-Loop Rule

`tree-loop` mode does not execute direct closed participant cycles. It executes local-close handoff trees or forests.

If source intent looks like:

```text
A -> B -> C -> A
```

either:
- clarify whether the user actually wants `generic-loop`; or
- normalize the tree-loop execution into a tree or forest.

## Normalization

When normalizing:
- choose an existing participant as relay, root, aggregator, or cycle breaker;
- do not create a synthetic participant;
- preserve local-close result return to immediate upstream;
- record the decision in process or topology artifacts;
- record it in ADRs when the current operation records decisions.

Example normalized execution:

```text
A -> B -> C
C -> B -> A   # result returns upstream through local-close replies
```

## Validation

Generated validation reports an error when:
- `tree-loop` topology contains a direct participant cycle;
- no accepted normalization explains the resulting tree or forest;
- a normal result bypasses immediate upstream without an explicit exception.
