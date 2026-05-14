## ADDED Requirements

### Requirement: Writer-team example routes operation through pro
The writer-team example SHALL route current loop operation instructions through `houmao-agent-loop-pro`.

The example SHALL NOT instruct users to run the retired `houmao-agent-loop-pairwise` package for current execution.

#### Scenario: Reader starts writer-team loop
- **WHEN** a reader follows the writer-team example start instructions
- **THEN** the instructions point to `houmao-agent-loop-pro`
- **AND THEN** the example identifies its topology as tree-loop behavior
