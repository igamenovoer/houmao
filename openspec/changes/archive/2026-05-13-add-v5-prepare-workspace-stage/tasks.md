## 1. Routing And Stage Surface

- [x] 1.1 Add `prepare-workspace` to the top-level operation list and execution routing in the loop skill.
- [x] 1.2 Update `agents/openai.yaml` short description if needed so workspace preparation is discoverable without making the prompt verbose.
- [x] 1.3 Keep operational prose generic and avoid version labels in skill body text except where file names, capability names, or explicit skill names require them.

## 2. Prepare-Workspace Subskill

- [x] 2.1 Add `subskills/execution/prepare-workspace.md` with read-first references, preconditions, inputs, actions, postconditions, report shape, and constraints.
- [x] 2.2 Define how `prepare-workspace` reads `execplan/manifest.toml`, `execplan/specs/workspace/workspace.toml`, and `execplan/agents/bindings.toml`.
- [x] 2.3 Define how `prepare-workspace` adapts generated workspace contracts into `houmao-utils-workspace-mgr` plan or execute inputs.
- [x] 2.4 Require plan-first behavior unless the user explicitly requests execution or has approved a current workspace plan.
- [x] 2.5 Require postcondition reporting for ready facts, planned-but-not-executed facts, missing facts, and inconsistencies.
- [x] 2.6 State that `prepare-workspace` does not install skills, create specialists, launch agents, bind mail support, or perform `prepare-agents`.

## 3. Prepare-Agents Boundary

- [x] 3.1 Revise `subskills/execution/prepare-agents.md` so workspace readiness is a precondition when required.
- [x] 3.2 Remove or rewrite guidance that implies `prepare-agents` should plan, execute, create, repair, or route workspace setup.
- [x] 3.3 Add an explicit constraint that `prepare-agents` does not call `prepare-workspace`.
- [x] 3.4 Add failure behavior for missing workspace readiness: stop and report missing `prepare-workspace` postconditions.

## 4. Generation And Validation Guidance

- [x] 4.1 Revise workspace-contract generation guidance so `execplan/specs/workspace/workspace.toml` contains workspace-manager inputs when managed workspaces are needed.
- [x] 4.2 Revise agent-binding guidance so `execplan/agents/bindings.toml` maps concrete agents/profiles and references workspace policy without replacing the workspace contract.
- [x] 4.3 Revise generated defaults or reference pages to document `prepare-workspace` as the workspace execution adapter and `prepare-agents` as the agent/profile/mail setup stage.
- [x] 4.4 Revise `validate-execplan` guidance to check workspace-manager routing, workspace contract completeness, postcondition readiness, and no cross-calling between `prepare-workspace` and `prepare-agents`.

## 5. Developer Documentation And Verification

- [x] 5.1 Update relevant `dev/design/` pages to explain the separate workspace and agent preparation stages.
- [x] 5.2 Check Markdown links and relative references for all modified skill pages.
- [x] 5.3 Run `openspec status --change add-v5-prepare-workspace-stage --json` and confirm the change is apply-ready.
- [x] 5.4 Run `git diff --check` before reporting the proposal complete.
