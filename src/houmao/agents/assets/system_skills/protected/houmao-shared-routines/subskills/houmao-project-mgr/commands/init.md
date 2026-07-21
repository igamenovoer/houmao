# Initialize The Project Overlay

Use this action only when the user wants to create or validate the selected Houmao project overlay.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Run `project init`.
3. Report the selected overlay root and the created or preserved paths from the command output.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> project init
```

## Guardrails

- Do not describe `project init` as creating `.houmao/mailbox/`, `.houmao/easy/`, or `.houmao/agents/` unconditionally.
- Do not use ambient discovery mode to pick a different root for `project init`; without `HOUMAO_PROJECT_OVERLAY_DIR`, the command bootstraps `<cwd>/.houmao`.
