## 1. Normalize shared operator wording primitives

- [x] 1.1 Update maintained shared help builders for runtime-root and mailbox-root options so server, cleanup, and mailbox surfaces describe active project roots versus explicit shared-root overrides consistently.
- [x] 1.2 Add or update maintained project-overlay wording helpers so non-creating failures, ownership-mismatch errors, and implicit-bootstrap notices use the selected-overlay vocabulary consistently.

## 2. Refresh maintained command-family text and payloads

- [x] 2.1 Update `src/houmao/srv_ctrl/commands/project.py` so project, project easy, and project mailbox help text, `ClickException` messages, and structured payload wording match the selected-overlay and implicit-bootstrap contract.
- [x] 2.2 Update `src/houmao/srv_ctrl/commands/mailbox.py`, `src/houmao/srv_ctrl/commands/admin.py`, `src/houmao/srv_ctrl/commands/brains.py`, `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/runtime_artifacts.py`, `src/houmao/server/commands/common.py`, and `src/houmao/passive_server/cli.py` so mailbox, cleanup, launch, and server wording matches the project-aware contract.
- [x] 2.3 Update any maintained human-oriented renderers or JSON-facing detail fields touched by those command families so selected-root and implicit-bootstrap information remains explicit without unnecessary payload churn.

## 3. Verify the wording contract

- [x] 3.1 Add or update focused unit coverage for help text, non-creating failures, ownership-mismatch errors, and bootstrap/result payload wording across the touched project, mailbox, cleanup, launch, and server surfaces.
- [x] 3.2 Run focused verification for the touched command families, including `ruff`, targeted `pytest`, and `openspec status --change refresh-project-aware-operator-wording`, then update `openspec/changes/make-operations-project-aware/tasks.md` to mark `4.6` complete.
