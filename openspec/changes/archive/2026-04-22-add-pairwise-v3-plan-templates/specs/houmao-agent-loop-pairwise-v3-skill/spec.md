## ADDED Requirements

### Requirement: Pairwise-v3 bundle plans may include generated template bundles
The authoring guidance in `houmao-agent-loop-pairwise-v3` SHALL support an authored `<plan-output-dir>/templates/` directory when a run needs reusable reporting or bookkeeping scaffolds.

When the authored run needs those reusable templates, the guidance SHALL direct the planner to use bundle form rather than single-file form.

The generated template bundle SHALL remain part of the authored plan output directory and SHALL NOT be described as runtime-owned state.

#### Scenario: Bundle plan includes generated reporting and bookkeeping templates
- **WHEN** a user authors a pairwise-v3 run whose reporting contract or bookkeeping posture needs reusable scaffolds
- **THEN** the authored output uses bundle form under the selected plan output directory
- **AND THEN** that bundle may include a `<plan-output-dir>/templates/` directory with generated reporting and bookkeeping templates

#### Scenario: Compact plan remains single-file when template bundle is unnecessary
- **WHEN** a user authors a compact pairwise-v3 run that does not need reusable reporting or bookkeeping scaffolds
- **THEN** the guidance may keep the plan in single-file form
- **AND THEN** it does not require inventing a `templates/` directory

### Requirement: Pairwise-v3 generated templates align with reporting and bookkeeping contracts
When `houmao-agent-loop-pairwise-v3` generates reporting templates, those templates SHALL reflect the authored reporting contract for the relevant run surfaces, including the applicable fields for peek, completion, recovery, stop, or hard-kill summaries when those surfaces are part of the run.

When `houmao-agent-loop-pairwise-v3` generates bookkeeping templates, those templates SHALL be derived from the task objective, topology, participant responsibilities, and declared bookkeeping paths for that run.

The guidance SHALL NOT impose one fixed bookkeeping subtree or one universal bookkeeping template set for all runs.

The guidance SHALL distinguish authored template files from mutable run artifacts written into declared bookkeeping paths, and SHALL NOT redefine Houmao runtime-owned recovery files as template-backed bookkeeping surfaces.

#### Scenario: Reporting template follows the authored reporting contract
- **WHEN** a pairwise-v3 bundle plan includes a reusable peek or completion template
- **THEN** that template reflects the fields required by the authored reporting contract for that report surface
- **AND THEN** the template does not invent a separate reporting schema unrelated to the contract

#### Scenario: Bookkeeping template stays task-shaped and boundary-aware
- **WHEN** a pairwise-v3 bundle plan includes reusable bookkeeping templates for a task-specific run
- **THEN** those templates are shaped by the run's objective, participant roles, topology, and declared bookkeeping paths
- **AND THEN** they do not prescribe one fixed per-agent `kb/` subtree or treat runtime-owned recovery files as ordinary bookkeeping artifacts
