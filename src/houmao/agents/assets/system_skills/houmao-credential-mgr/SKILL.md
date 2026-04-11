---
name: houmao-credential-mgr
description: Use Houmao's supported credential workflow to list, inspect, add, update, log in, rename, or remove credentials for the active project overlay or an explicit plain agent-definition directory.
license: MIT
---

# Houmao Credential Manager

Use this Houmao skill when you need to manage credentials through the supported CLI surfaces:

- `houmao-mgr project credentials <tool> ...` for the active project overlay
- `houmao-mgr credentials <tool> ... --agent-def-dir <path>` for an explicit plain agent-definition directory

Do not hand-edit `.houmao/content/auth/`, `.houmao/agents/tools/<tool>/auth/`, or `tools/<tool>/auth/<name>/` directly when these command families already own the workflow.

For project-backed credentials, operator-facing names remain mutable display names resolved through the project catalog while projected directory basenames remain opaque implementation detail.

For plain agent-definition directories, credential identity is the directory basename under `tools/<tool>/auth/<name>/`, and direct-dir rename also rewrites maintained auth references under `presets/*.yaml` and `launch-profiles/*.yaml`.

The trigger word `houmao` is intentional. Use the `houmao-credential-mgr` skill name directly when you intend to activate this Houmao-owned skill.

## Scope

This packaged skill covers exactly these credential actions:

- `list`
- `get`
- `add`
- `set`
- `login`
- `rename`
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
- direct filesystem editing under `.houmao/content/auth/`
- direct filesystem editing under `.houmao/agents/tools/`
- direct filesystem editing under `tools/<tool>/auth/`

## Workflow

1. Identify which credential-management action the user wants: `list`, `get`, `add`, `set`, `login`, `rename`, or `remove`.
2. If the request is really about changing which credential a reusable profile stores for later launches, stop and route it before continuing:
   - easy-profile auth override work belongs to `houmao-specialist-mgr`
   - explicit launch-profile auth override work belongs to the supported `houmao-mgr project agents launch-profiles add|set --auth ...` or `--clear-auth` surface, not to credential CRUD
3. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
4. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
5. Recover the target:
   - use `project credentials <tool> ...` when the request is clearly project-local or the active project overlay is the intended target
   - use `credentials <tool> ... --agent-def-dir <path>` when the user explicitly targets a plain agent-definition directory
   - ask before proceeding when the target is still ambiguous
6. Reuse that same chosen launcher for the selected credential-management action.
7. Load exactly one action page:
   - `actions/list.md`
   - `actions/get.md`
   - `actions/add.md`
   - `actions/set.md`
   - `actions/login.md`
   - `actions/rename.md`
   - `actions/remove.md`
8. Follow the selected action page and report the result from the command that ran.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - a short bullet list when only one or two fields are missing
  - a compact table when the tool lane, target, or several required fields need clarification
- Name the command you intend to run and show only the missing fields needed for that command.

## Routing Guidance

- Use `actions/list.md` only when the user wants to list credentials for one supported tool.
- Use `actions/get.md` only when the user wants to inspect one credential safely through redacted CLI output.
- Use `actions/add.md` only when the user wants to create one new credential.
- Use `actions/set.md` only when the user wants to update one existing credential.
- Use `actions/login.md` only when the user wants to run a provider login flow for a fresh Claude, Codex, or Gemini account and import the resulting auth files into Houmao storage.
- Use `actions/rename.md` only when the user wants to rename one existing credential.
- Use `actions/remove.md` only when the user wants to remove one existing credential.
- When the user wants to change the stored `--auth` override on an easy profile or explicit launch profile, do not use this skill's action pages; that is profile authoring rather than credential mutation.

## Guardrails

- Do not guess the intended action when the prompt could mean specialist authoring, live-agent lifecycle work, or credential management.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not scan env vars, tool homes, home directories, or unrelated filesystem locations to infer missing credential inputs unless the user explicitly asks for that narrower inspection.
- Do not print raw secret values or raw auth-file contents when `get` already provides safe redacted inspection.
- Do not hand-roll provider-login temp directories, manual provider command invocation, auth-file copying, or temp cleanup when `houmao-mgr credentials <tool> login` owns that ordinary workflow.
- Do not treat changing an easy profile or explicit launch profile `--auth` override as credential CRUD.
- Do not imply that project-backed rename changes underlying bundle identity; it is metadata-only rename.
- Do not imply that direct-dir rename is a no-op for maintained references; it rewrites maintained `presets/*.yaml` and `launch-profiles/*.yaml` auth references for that selected tool.
- Do not invent provider-neutral credential flags, unsupported clear flags, or file inputs that the selected tool surface does not actually support.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not use deprecated `houmao-cli` or `houmao-cao-server` entrypoints for credential management.
