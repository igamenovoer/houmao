---
name: houmao-credential-mgr
description: Use Houmao's supported credential workflow to list, inspect, add, update, log in, rename, or remove credentials for a Houmao project or an internal native-agent root.
license: MIT
---

# Houmao Credential Manager

## Actor Frame Gate

This protected routine is admin-only and MUST NOT execute standalone. Require `actor_kind=admin` and `entrypoint_name=houmao-admin-entrypoint`, plus an explicit project or native-agent credential target. Reject agent frames and never disclose credential values in route traces, questions, or provenance.

Use this Houmao skill when you need to manage credentials through the supported CLI surfaces:

- `houmao-mgr project [--project-dir <dir>] credentials <tool> ...` for project-backed credentials
- `houmao-mgr internals native-agent credentials <tool> ... --native-agent-root <path>` for direct native-agent credentials

Do not hand-edit `.houmao/content/auth/`, `.houmao/agents/tools/<tool>/auth/`, or `tools/<tool>/auth/<name>/` directly when these command families already own the workflow.

For project-backed credentials, operator-facing names remain mutable display names resolved through the project catalog while projected directory basenames remain opaque implementation detail.

For plain agent-definition directories, credential identity is the directory basename under `tools/<tool>/auth/<name>/`, and direct-dir rename also rewrites maintained auth references under `presets/*.yaml` and `launch-profiles/*.yaml`.

The trigger word `houmao` is intentional. Enter this protected routine only through the actor-qualified route `<public-entrypoint>->houmao-shared-routines->credential-mgr`; never invoke its logical id as a standalone skill.

## Help

When the user asks `$<public-entrypoint> credential-mgr help`, `help for houmao-credential-mgr`, `usage for houmao-credential-mgr`, `available functionality for houmao-credential-mgr`, or what this skill can do, answer from this section before choosing a credential action, command, reference page, or missing-input question. This is read-only help: do not run commands, mutate files, send mail, change gateway state, or alter managed-agent lifecycle state during help. If the user asks a concrete task such as "help me add a Codex credential", route to the matching workflow instead of stopping at generic help.

Purpose: manage supported Houmao credential bundles for project overlays or internal native-agent roots.

Available functionality:

- `list` and `get` credentials with safe inspection posture.
- `add` and `set` credential bundle contents for supported tool families.
- `login` through maintained Claude and Codex provider login/import workflows.
- Kimi Code OAuth login handling through `kimi login` in an isolated `KIMI_CODE_HOME`, followed by existing Kimi `add` or `set --code-home` import.
- `rename` or `remove` one existing credential.
- Choose project-backed versus direct native-agent targets.

Common starting prompts:

- `$<public-entrypoint> credential-mgr help`
- `$<public-entrypoint> credential-mgr list codex credentials`
- `$<public-entrypoint> credential-mgr add claude credential`
- `$<public-entrypoint> credential-mgr login kimi`
- `$<public-entrypoint> credential-mgr add kimi credential`

Related skills and boundaries:

- Use `<public-entrypoint>->houmao-shared-routines->agent-definition` to change stored `--auth` overrides on project profiles or native launch dossiers.
- Use `<public-entrypoint>->houmao-shared-routines->project-mgr` for project overlay lifecycle and status.
- Use `<public-entrypoint>->houmao-shared-routines->agent-instance` for launch, join, list, stop, or cleanup.
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

- `houmao-mgr project specialist ...`
- `houmao-mgr project profile ...`
- `houmao-mgr project agents ...`
- `houmao-mgr agents global|single|self|external ...`
- `houmao-mgr internals native-agent launch-dossiers ...`
- `houmao-mgr internals native-agent tools <tool> setups ...`
- `houmao-mgr internals native-agent roles ...`
- `houmao-mgr project mailbox ...`
- managed-agent cleanup or mailbox participation surfaces
- `houmao-mgr admin cleanup runtime ...`
- direct filesystem editing under `.houmao/content/auth/`
- direct filesystem editing under `.houmao/agents/tools/`
- direct filesystem editing under `tools/<tool>/auth/`

## Workflow

Before starting the workflow, answer explicit skill-help intent from `## Help` and stop.

1. Identify which credential-management action the user wants: `list`, `get`, `add`, `set`, `login`, `rename`, or `remove`.
2. If the request is really about changing which credential a reusable profile stores for later launches, stop and route it before continuing:
   - project-profile auth override work belongs to `<public-entrypoint>->houmao-shared-routines->agent-definition`
   - launch-dossier auth override work belongs to `<public-entrypoint>->houmao-shared-routines->agent-definition` subcommand `launch-dossiers`, not to credential CRUD
3. If the requested action is still ambiguous after checking the current prompt and recent chat context, ask the user before proceeding.
4. Choose one `houmao-mgr` launcher for the current turn:
   - first run `command -v houmao-mgr` and use the `houmao-mgr` already on `PATH` when present
   - if that lookup fails, use `uv tool run --from houmao houmao-mgr`
   - only if the PATH lookup and uv-managed fallback do not satisfy the turn, choose the appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`
   - if the user explicitly asks for a specific launcher, follow that request instead of the default order
5. Recover the target:
   - use `project [--project-dir <dir>] credentials <tool> ...` when the request is project-local or names a project directory
   - use `internals native-agent credentials <tool> ... --native-agent-root <path>` when the user explicitly targets a native-agent root
   - ask before proceeding when the target is still ambiguous
6. Reuse that same chosen launcher for the selected credential-management action.
7. For supported credential command authoring, build the direct maintained command with only fields the user explicitly supplied or that were recovered from explicit recent context:
   - project lane: `project credentials <tool> <verb>`
   - direct native-agent lane: `internals native-agent credentials <tool> <verb>`
   - supported CRUD tools: `claude`, `codex`, `kimi`
   - supported login-helper tools: `claude`, `codex`
   - supported CRUD verbs: `add`, `set`, `list`, `get`, `rename`, `remove`
   - supported login-helper verb: `login`
   - Kimi Code login/import requests use `references/kimi-code-login-handling.md` and must end in an existing Kimi `add` or `set --code-home` import, not a `credentials kimi login` helper command
8. If required input is missing or explicit inputs conflict, stop and recover the missing or conflicting input before running the target command.
10. Load exactly one action page:
   - `commands/list.md`
   - `commands/get.md`
   - `commands/add.md`
   - `commands/set.md`
   - `commands/login.md`
   - `commands/rename.md`
   - `commands/remove.md`
   - for explicit Kimi Code OAuth login/import, use `references/kimi-code-login-handling.md` instead of inventing a maintained Kimi login helper
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

- Use `commands/list.md` only when the user wants to list credentials for one supported tool.
- Use `commands/get.md` only when the user wants to inspect one credential safely through redacted CLI output.
- Use `commands/add.md` only when the user wants to create one new credential.
- Use `commands/set.md` only when the user wants to update one existing credential.
- Use `commands/login.md` only when the user wants to run a maintained provider login helper for a fresh Claude or Codex account and import the resulting auth files into Houmao storage.
- Use `references/kimi-code-login-handling.md` only when the user wants a fresh default Kimi Code OAuth login through `kimi login` and import through Kimi `add` or `set --code-home`.
- Use `commands/rename.md` only when the user wants to rename one existing credential.
- Use `commands/remove.md` only when the user wants to remove one existing credential.
- When the user wants to change the stored `--auth` override on a project profile or native launch dossier, do not use this skill's action pages; that is profile or launch-dossier authoring rather than credential mutation.

## Guardrails

- Do not guess the intended action when the prompt could mean specialist authoring, live-agent lifecycle work, or credential management.
- Do not guess required action inputs that remain missing after checking the prompt and recent chat context.
- Do not scan env vars, tool homes, home directories, or unrelated filesystem locations to infer missing credential inputs unless the user explicitly asks for that narrower inspection.
- Do not print raw secret values or raw auth-file contents when `get` already provides safe redacted inspection.
- Do not hand-roll provider-login temp directories, manual provider command invocation, auth-file copying, or temp cleanup when maintained project or internal native-agent credential login commands own that workflow.
- Do not present Kimi as having a maintained credential login helper; Kimi Code login handling must use the Kimi-specific reference workflow and finish with existing Kimi `add` or `set --code-home` import.
- Do not treat changing a project profile or native launch dossier `--auth` override as credential CRUD.
- Do not imply that project-backed rename changes underlying bundle identity; it is metadata-only rename.
- Do not imply that direct-dir rename is a no-op for maintained references; it rewrites maintained `presets/*.yaml` and `launch-profiles/*.yaml` auth references for that selected tool.
- Do not invent provider-neutral credential flags, unsupported clear flags, or file inputs that the selected tool surface does not actually support.
- Do not skip `command -v houmao-mgr` as the default first step unless the user explicitly requests a different launcher.
- Do not probe Pixi, repo-local `.venv`, or project-local `uv run` before the PATH check and uv fallback unless the user explicitly asks for one of those launchers.
- Do not use deprecated `houmao-cli` or removed standalone CAO launcher workflows for credential management.

## References

- `references/claude-credential-kinds.md` — explanatory credential-kind notes for Claude when a user needs help choosing input material
- `references/codex-credential-kinds.md` — explanatory credential-kind notes for Codex when a user needs help choosing input material
- `references/kimi-credential-kinds.md` — explanatory credential-kind notes for Kimi when a user needs help choosing input material
- `references/kimi-code-login-handling.md` — Kimi-specific default OAuth login/import workflow using `kimi login`, isolated `KIMI_CODE_HOME`, tmux, and `--code-home`
