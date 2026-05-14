## 1. Skill Routing

- [x] 1.1 Invoke `$skill-creator` before editing the packaged skill assets.
- [x] 1.2 Add the six staged execplan generation subcommands to the top-level skill operation list and routing table.
- [x] 1.3 Update `generate-execplan` to present itself as the orchestration command that runs the staged subcommands in order.
- [x] 1.4 Update `update-execplan` to explain earliest-affected-stage selection and downstream stage reruns.

## 2. Stage Subskills

- [x] 2.1 Add or update authoring guidance for `execplan-specs-process` as the first generated stage.
- [x] 2.2 Add or update authoring guidance for `execplan-specs-contract` as the stage that derives objective, participants, topology, comms, state, records, workspace, and run contracts from the process model.
- [x] 2.3 Add or update authoring guidance for `execplan-harness` as the stage that generates loop-local validation, query, render, explain, completion, and controlled-apply surfaces from contracts.
- [x] 2.4 Add or update authoring guidance for `execplan-skills` as the stage that generates shared harness, role event, tick, and operator skills from process/contracts/harness.
- [x] 2.5 Add or update authoring guidance for `execplan-agent-bindings` as the stage that generates concrete agent configs and definitions after generated skills exist.
- [x] 2.6 Add or update authoring guidance for `execplan-finalize` as the final docs, README, manifest, metadata, omission, and consistency stage.

## 3. Validation And Design Docs

- [x] 3.1 Update `validate-execplan` guidance to check staged-generation posture, process-first dependency order, and final manifest consistency.
- [x] 3.2 Update developer design notes to document the process-first staged generation model and dependency graph.
- [x] 3.3 Update `agents/openai.yaml` so UI-facing metadata mentions staged execplan generation without overloading the default prompt.

## 4. Verification

- [x] 4.1 Run OpenSpec status or validation for `add-staged-execplan-generation` and resolve artifact issues.
- [x] 4.2 Run skill validation for the packaged skill.
- [x] 4.3 Check for stale command names, stale links, accidental domain-specific defaults, and Markdown whitespace issues.
