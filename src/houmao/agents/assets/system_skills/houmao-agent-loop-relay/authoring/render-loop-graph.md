# Render The Final Relay Graph

Use this page when the authored plan needs the final Mermaid graph that shows who may hand off to whom, where the loop lives, and where stop and completion are checked.

The final plan must include one Mermaid fenced code block. Do not use ASCII art as the primary graph representation.

## What The Graph Must Show

At minimum, the top-level graph must show:

- the user agent outside the execution loop
- the designated master as the loop origin and root run owner
- the relay handoff edges between upstream and downstream agents
- where immediate receipts flow back to the previous sender
- where the final result returns from the loop egress to the origin
- where the supervision loop lives
- where the completion condition is evaluated
- where the stop condition is evaluated

## Graph Semantics

- Draw execution edges as forward relay handoffs.
- Draw per-hop receipts as immediate upstream acknowledgements rather than as final completion.
- Draw the final-result return from the loop egress back to the origin.
- Draw the supervision loop as a review cycle owned by the origin, not as a worker-to-worker cycle.
- Keep labels short and wrap with `<br/>` when needed.
- Split a very large topology into one top-level diagram plus supporting subtree diagrams instead of making one unreadable diagram.

## Example

```mermaid
flowchart TD
    UA[User Agent<br/>control only]
    O[Master / Origin<br/>root run owner]
    OL[Origin Loop<br/>review active routes<br/>check completion<br/>check stop]
    I[Loop Ingress]
    R[Relay Agent]
    E[Loop Egress]
    Done[Completion Condition<br/>user-defined]
    Stop[Stop Condition<br/>default: interrupt-first]

    UA -->|start plan| O
    UA -.->|status| O
    UA ==> |stop| O

    O -->|handoff h1| I
    I -.->|receipt h1| O
    I -->|handoff h2| R
    R -.->|receipt h2| I
    R -->|handoff h3| E
    E -.->|receipt h3| R
    E ==> |final result| O

    O --> OL
    OL --> Done
    OL --> Stop
    OL -->|advance run| O
```

## Guardrails

- Do not imply that the user agent is an execution participant by drawing receipt or result ownership on the user agent.
- Do not draw the loop as an arbitrary cyclic worker graph when the real loop is the origin's supervision cycle.
- Do not omit the stop condition, completion condition, or final-result return path from the final plan graph.
