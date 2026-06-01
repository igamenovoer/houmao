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

## Help

When the user asks `$houmao-credential-mgr help`, `help for houmao-credential-mgr`, `usage for houmao-credential-mgr`, `available functionality for houmao-credential-mgr`, or what this skill can do, answer from this section before choosing a credential action, command, reference page, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me add a Codex credential", route to the matching workflow instead of stopping at generic help.

Purpose: manage supported Houmao credential bundles for project overlays or explicit plain agent-definition directories.

Available functionality:

- `list` and `get` credentials with safe inspection posture.
- `add` and `set` credential bundle contents for supported tool families.
- `login` through maintained provider login/import workflows.
- `rename` or `remove` one existing credential.
- Choose project-backed versus explicit plain agent-definition directory targets.

Common starting prompts:

- `$houmao-credential-mgr help`
- `$houmao-credential-mgr list codex credentials`
- `$houmao-credential-mgr add claude credential`
- `$houmao-credential-mgr login gemini`

Related skills and boundaries:

- Use `houmao-agent-definition` to change stored `--auth` overrides on easy or raw launch profiles.
- Use `houmao-project-mgr` for project overlay lifecycle and status.
- Use `houmao-agent-instance` for launch, join, list, stop, or cleanup.
- Do not use this skill for direct filesystem editing under credential storage directories.

## Scope

This packaged skill covers exactly these credential actions:

- `help` (read-only meta operation)
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

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Identify which credential-management action the user wants: `list`, `get`, `add`, `set`, `login`, `rename`, or `remove`.
2. If the request is really about changing which credential a reusable profile stores for later launches, stop and route it before continuing:
   - easy-profile auth override work belongs to `houmao-agent-definition`
   - raw-profile auth override work belongs to `houmao-agent-definition` subcommand `raw-profiles`, not to credential CRUD
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
7. For supported credential command authoring, inspect and render the matching CLI-owned template id before executing:
   - project lane: `project.credentials.<tool>.<verb>`
   - plain agent-definition lane: `credentials.<tool>.<verb>`
   - supported tools: `claude`, `codex`, `gemini`
   - supported verbs: `add`, `set`, `login`, `list`, `get`, `rename`, `remove`
8. Render sparse intent with only fields the user explicitly supplied or that were recovered from explicit recent context:
   - `<chosen houmao-mgr launcher> --print-json internals command-templates show --id <template-id>`
   - `<chosen houmao-mgr launcher> --print-json internals command-templates render --id <template-id> --intent '<json>'`
9. If render output has blockers, stop and recover the missing or conflicting input before running the target command.
10. Load exactly one action page:
   - `actions/list.md`
   - `actions/get.md`
   - `actions/add.md`
   - `actions/set.md`
   - `actions/login.md`
   - `actions/rename.md`
   - `actions/remove.md`
11. Follow the selected action page and report the result from the command that ran.

## Missing Input Questions

- Recover required values from the current prompt first and recent chat context second, but only when the user stated them explicitly.
- If any required input is still missing after that check, ask the user for exactly the missing fields instead of guessing.
- When asking for missing input, use readable Markdown:
  - separate `Required` values from `Optional` modifiers
  - `Required`: values that block the selected credential command, such as action, tool family, target, credential name, supported credential input, supported change, or rename target
  - `Optional`: launcher preference, output format, credential-kind modifiers, defaults, or skip choices; if none apply, say `Optional: none for this step.`
  - use a short bullet list when only one or two required fields are missing
  - use a compact table when the tool lane, target, or several required fields need clarification
- Name the command you intend to run and show only the missing fields needed for that command.
- Do not use this format for user-task or domain-intent questions unless the question is about Houmao runtime behavior.

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
- Do not hand-author covered credential commands or tool-specific option menus from Markdown when `internals command-templates render` supports the surface.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not use deprecated `houmao-cli` or removed standalone CAO launcher workflows for credential management.

## References

- `references/claude-credential-kinds.md` — explanatory credential-kind notes for Claude when a user needs help choosing input material
- `references/codex-credential-kinds.md` — explanatory credential-kind notes for Codex when a user needs help choosing input material
- `references/gemini-credential-kinds.md` — explanatory credential-kind notes for Gemini when a user needs help choosing input material
