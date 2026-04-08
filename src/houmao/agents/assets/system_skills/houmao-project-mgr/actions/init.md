# Initialize The Project Overlay

Use this action only when the user wants to create or validate the selected Houmao project overlay.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Decide whether the user wants the ordinary project overlay bootstrap or also wants the optional compatibility-profiles subtree pre-created.
3. If the request is ambiguous about whether compatibility profiles should be pre-created, ask before proceeding.
4. Run the matching `project init` command.
5. Report the selected overlay root and the created or preserved paths from the command output.

## Command Shape

Use one of:

```text
<chosen houmao-mgr launcher> project init
<chosen houmao-mgr launcher> project init --with-compatibility-profiles
```

## Guardrails

- Do not guess whether `--with-compatibility-profiles` is wanted when the user did not ask for it.
- Do not describe `project init` as creating `.houmao/mailbox/`, `.houmao/easy/`, or `.houmao/agents/` unconditionally.
- Do not use ambient discovery mode to pick a different root for `project init`; without `HOUMAO_PROJECT_OVERLAY_DIR`, the command bootstraps `<cwd>/.houmao`.
