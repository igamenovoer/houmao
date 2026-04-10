# `plan.md` Template

~~~~md
# Objective
<what the loop is trying to accomplish>

# Loop Kind
<pairwise | relay>

# Master
<designated master>

# Participants
See `participants.md`.

# Execution
See `execution.md`.

# Distribution
See `distribution.md`.

# Completion
<short completion summary>

# Stop
<short stop summary>

# Mermaid Graph
```mermaid
flowchart TD
    OP[Operator<br/>outside execution]
    M[Master]
    Loop[Supervision Loop]
    Done[Completion]
    Stop[Stop]

    OP -->|prepare and hand off later| M
    M --> Loop
    Loop --> Done
    Loop --> Stop
```
~~~~
