## 1. Shared Contract Surfaces

- [ ] 1.1 Add shared loop-run contract guidance for `workspace_contract` and `bookkeeping_contract`, including `standard` versus `custom` posture vocabulary.
- [ ] 1.2 Update loop plan templates and reference pages so standard workspace mode reuses `in-repo` or `out-of-repo` posture and standard bookkeeping mode requires explicit declared locations without a fixed `kb/` subtree.

## 2. Loop Skill Updates

- [ ] 2.1 Update `houmao-agent-loop-pairwise` authoring and operating assets to require explicit workspace and bookkeeping contracts in accepted run plans.
- [ ] 2.2 Update `houmao-agent-loop-pairwise-v2` authoring, prestart, and operating assets to preserve declared workspace/bookkeeping contracts and keep mutable bookkeeping out of managed-memory ledgers.
- [ ] 2.3 Update `houmao-agent-loop-generic` authoring and operating assets to require explicit workspace and bookkeeping contracts in authored generic run plans.

## 3. Workspace-Manager Integration

- [ ] 3.1 Update `houmao-utils-workspace-mgr` guidance so prepared in-repo and out-of-repo workspaces can publish loop-facing standard posture summaries.
- [ ] 3.2 Ensure workspace-manager loop-facing summaries describe writable zones and ad hoc worktree posture without prescribing a fixed per-agent bookkeeping tree.

## 4. Documentation

- [ ] 4.1 Update `docs/getting-started/loop-authoring.md` to document the new workspace and bookkeeping contract model, including standard/custom posture and explicit bookkeeping-path rules.
- [ ] 4.2 Refresh any affected loop-facing examples or supporting references so they show the new contract sections consistently.

## 5. Verification

- [ ] 5.1 Add or update focused checks that cover the loop authoring guide and any affected packaged asset text that now carries workspace/bookkeeping contract requirements.
- [ ] 5.2 Run the relevant focused validation for the changed docs/assets and confirm the OpenSpec change is apply-ready.
