## 1. Inventory System-Input Questions

- [x] 1.1 Search packaged Houmao system skills for user-question guidance using `rg` over `ask the user`, `missing input`, `Missing Input Questions`, and related wording.
- [x] 1.2 Classify each hit as Houmao system-operation input or user-task/domain-intent input.
- [x] 1.3 Leave user-task/domain-intent questions unchanged unless the specific question asks for Houmao runtime behavior.

## 2. Update Shared And Direct-Operation Guidance

- [x] 2.1 Add the required/optional system-input rule to shared missing-input guidance used by direct-operation skills.
- [x] 2.2 Update direct manager skills that ask for Houmao system inputs, including agent definition, credentials, project overlay, mailbox, gateway, messaging, inspection, memory, instance lifecycle, and workspace management pages.
- [x] 2.3 Keep action pages concise by routing to shared guidance where possible instead of duplicating long policy text.

## 3. Update Guided And Loop Guidance

- [x] 3.1 Update `houmao-touring` question guidance so system setup questions label required values and optional defaults or skip paths while preserving examples and explanations.
- [x] 3.2 Update `houmao-agent-loop-pro` system-operation subcommands and shared references to label required and optional Houmao runtime inputs.
- [x] 3.3 Update `houmao-agent-loop-pairwise-v5` system-operation subcommands and shared references with the same boundary, without adding version-lineage wording to user-facing body text.
- [x] 3.4 Patch other Houmao loop run-control pages only where they ask for Houmao system inputs such as loop directory, run target, launch target, or lifecycle action.

## 4. Tests And Validation

- [x] 4.1 Add focused unit tests in `tests/unit/agents/test_system_skills.py` for shared missing-input guidance and representative touring/loop pages.
- [x] 4.2 Run `openspec validate --all`.
- [x] 4.3 Run focused system-skill tests with `pixi run pytest tests/unit/agents/test_system_skills.py -q`.
- [x] 4.4 Run `git diff --check`.
