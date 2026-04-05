---
name: houmao-create-specialist
description: Use Houmao's supported project-easy specialist workflow to create one reusable specialist with the correct `houmao-mgr` launcher for the current environment.
license: MIT
---

# Houmao Create Specialist

Use this Houmao skill when you need to create one reusable easy specialist through Houmao's supported higher-level authoring command instead of hand-editing project files.

The trigger word `houmao` is intentional. Use the `houmao-create-specialist` skill name directly when you intend to activate this Houmao-owned skill.

## Workflow

1. Collect the user's intended specialist inputs from the current prompt first.
2. If some necessary inputs are missing, look in recent chat context for exact previously stated values.
3. If the specialist name or tool lane is still missing, ask the user before proceeding.
4. Resolve the intended credential name. If the user did not provide `--credential`, use the documented CLI default `<specialist-name>-creds`.
5. If auth inputs are not present, confirm whether that credential bundle already exists for the selected tool. Use the same resolved `houmao-mgr` launcher for `project agents tools <tool> auth get --name <credential>` or `list` when you need that confirmation.
6. If the credential bundle is not confirmed to exist and required auth inputs are still missing after checking current prompt and recent chat context, ask the user for the missing auth inputs instead of guessing.
7. Resolve the correct `houmao-mgr` launcher for the current workspace in this order:
   - repo-local `.venv/bin/houmao-mgr`
   - `pixi run houmao-mgr` when the workspace shows development-project hints such as `pixi.lock`, `.pixi/`, `pixi.toml`, or a Pixi-managed `pyproject.toml`
   - `uv run houmao-mgr` when the workspace shows project-local uv hints such as `uv.lock` or a uv-managed `pyproject.toml`
   - globally installed `houmao-mgr` from uv tools for the ordinary end-user case
8. Run `project easy specialist create` through that resolved launcher.
9. Report the created specialist, selected tool, resolved credential name, and the generated artifact paths returned by the command.

## Required Inputs

- `--name`
- `--tool`
- enough auth input for the selected tool unless the intended credential bundle already exists

`--system-prompt` and `--system-prompt-file` are both optional. Use at most one of them.

## Command Shape

Use the resolved launcher with:

```text
<resolved houmao-mgr launcher> project easy specialist create --name <name> --tool <tool> ...
```

Use these documented defaults and options exactly:

- `--credential` defaults to `<name>-creds` when omitted
- `--setup` defaults to `default` when omitted
- `--no-unattended` is the explicit opt-out from the easy unattended default
- repeatable `--with-skill <dir>` imports selected skill directories
- repeatable `--env-set NAME=value` persists non-credential launch env

Tool-specific auth inputs:

- Claude: `--api-key`, optional `--base-url`, optional `--claude-auth-token`, optional `--claude-model`, optional `--claude-state-template-file`
- Codex: `--api-key`, optional `--base-url`, optional `--codex-org-id`, optional `--codex-auth-json`
- Gemini: `--api-key`, optional `--base-url`, optional `--google-api-key`, optional `--use-vertex-ai`, optional `--gemini-oauth-creds`

## Guardrails

- Do not guess the specialist name, tool lane, or auth values.
- Do not invent API keys, org ids, auth file paths, OAuth credential files, or base URLs.
- Do not mix `--system-prompt` and `--system-prompt-file`.
- Do not treat missing auth as optional unless the intended credential bundle is confirmed to already exist.
- Do not force `pixi run houmao-mgr` when the workspace is not a development project.
- Do not ignore a repo-local `.venv` launcher just because Pixi or uv hints are also present.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for specialist authoring.
