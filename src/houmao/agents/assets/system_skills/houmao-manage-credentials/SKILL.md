---
name: houmao-manage-credentials
description: Use Houmao's supported project-local auth-bundle workflow to list, inspect, add, update, or remove credentials with the correct `houmao-mgr` launcher for the current environment. This skill manages auth bundles themselves, not stored profile-level auth overrides.
license: MIT
---

# Houmao Manage Credentials

Use this Houmao skill when you need to manage project-local tool auth bundles through `houmao-mgr project agents tools <tool> auth ...` instead of hand-editing `.houmao/agents/tools/`.

The trigger word `houmao` is intentional. Use the `houmao-manage-credentials` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these `project agents tools <tool> auth` actions:

- `list`
- `get`
- `add`
- `set`
- `remove`

This packaged skill does not cover:

- `houmao-mgr project easy specialist ...`
- `houmao-mgr project easy profile ...`
- `houmao-mgr project easy instance ...`
- `houmao-mgr agents launch|join|list|stop|cleanup`
- `houmao-mgr project agents launch-profiles ...`
- `houmao-mgr project agents tools <tool> setups ...`
- `houmao-mgr project agents roles ...`
- `houmao-mgr project mailbox ...`
- `houmao-mgr agents cleanup mailbox`
- `houmao-mgr admin cleanup runtime ...`
- direct filesystem editing under `.houmao/agents/tools/`

## Workflow

1. Identify which credential-management action the user wants: `list`, `get`, `add`, `set`, or `remove`.
2. If the request is really about changing which auth bundle a reusable profile stores for later launches, stop and route it before continuing:
   - easy-profile auth override work belongs to `houmao-manage-specialist`
   - explicit launch-profile auth override work belongs to the supported `houmao-mgr project agents launch-profiles add|set --auth ...` or `--clear-auth` surface, not to auth-bundle CRUD
3. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
4. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
5. Reuse that same chosen launcher for the selected credential-management action.
6. Load exactly one action page:
   - `actions/list.md`
   - `actions/get.md`
   - `actions/add.md`
   - `actions/set.md`
   - `actions/remove.md`
7. Follow the selected action page and report the result from the command that ran.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the tool lane or several required fields need clarification
- Name the command you intend to run and show only the missing fields needed for that command.

## Routing Guidance

- Use `actions/list.md` only when the user wants to list auth bundles for one supported tool.
- Use `actions/get.md` only when the user wants to inspect one auth bundle safely through redacted CLI output.
- Use `actions/add.md` only when the user wants to create one new auth bundle.
- Use `actions/set.md` only when the user wants to update one existing auth bundle.
- Use `actions/remove.md` only when the user wants to remove one existing auth bundle.
- When the user wants to change the stored `--auth` override on an easy profile or explicit launch profile, do not use this skill's action pages; that is profile authoring rather than auth-bundle mutation.

## Guardrails

- Do not guess the intended action when the prompt could mean specialist authoring, live-agent lifecycle work, or credential management.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not scan env vars, tool homes, home directories, or unrelated filesystem locations to infer missing auth inputs unless the user explicitly asks for that narrower inspection.
- Do not print raw secret values or raw auth-file contents when `auth get` already provides safe redacted inspection.
- Do not treat changing an easy profile or explicit launch profile `--auth` override as `auth add|set|remove`.
- Do not imply that auth-bundle CRUD automatically rewrites stored auth references on specialists, easy profiles, explicit launch profiles, or live instances.
- Do not invent provider-neutral credential flags, unsupported clear flags, or file inputs that the selected tool's `auth` surface does not actually support.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for credential management.
