## 1. Pairwise-V3 Skill

- [x] 1.1 Add the packaged `houmao-agent-loop-pairwise-v3` skill as the workspace-aware extension of pairwise-v2.
- [x] 1.2 Author pairwise-v3 plan, reference, and operating assets so the workspace contract supports `standard` and `custom` modes.
- [x] 1.3 Ensure pairwise-v3 preserves pairwise-v2 recovery boundaries and keeps runtime-owned recovery files outside the authored workspace contract.

## 2. Standard Workspace Integration

- [x] 2.1 Redefine the standard in-repo workspace posture as task-scoped under `houmao-ws/<task-name>/...`, including task-local `workspace.md`, task-local `shared-kb`, and task-qualified branch naming.
- [x] 2.2 Update `houmao-utils-workspace-mgr` guidance so it remains the standard workspace-preparation skill and does not gain a custom-workspace lane.
- [x] 2.3 Ensure workspace-manager loop-facing summaries describe the reusable standard workspace contract without prescribing a fixed per-agent bookkeeping tree.

## 3. Catalog And Documentation

- [x] 3.1 Update packaged system-skill installation/catalog expectations so `houmao-agent-loop-pairwise-v3` is a current installable skill in the pairwise family.
- [x] 3.2 Update `docs/getting-started/loop-authoring.md` to explain pairwise-v2 versus pairwise-v3, standard versus custom workspace mode, and task-scoped standard in-repo posture.
- [x] 3.3 Refresh any affected loop-facing examples or supporting references so they point at pairwise-v3 where workspace-aware planning is intended.

## 4. Verification

- [x] 4.1 Add or update focused checks that cover the new pairwise-v3 packaged asset text and the updated loop authoring guide.
- [x] 4.2 Run the relevant focused validation for the changed docs/assets and confirm the OpenSpec change is apply-ready.
