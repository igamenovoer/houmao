## Context

Houmao’s command surface has accumulated several sparse, default-sensitive authoring flows: easy specialists, easy profiles, raw launch profiles, managed headers, prompt overlays, mailbox bindings, model/reasoning defaults, prompt mode, and TUI/headless posture. The CLI owns the actual semantics, but packaged skills currently carry enough Markdown guidance that they can accidentally become a second source of truth.

The recent prompt-mode issue is the concrete failure mode: the skill can teach agents to persist `--prompt-mode unattended` as a default when the intended authoring move is to omit `prompt_mode` and let the launcher default resolve. The same class of problem can recur for headless posture, managed-header inheritance, skill inheritance, mailbox defaults, and clear-vs-omit patch behavior.

## Goals / Non-Goals

**Goals:**

- Make the CLI the authoritative source for agent-facing command templates and sparse default semantics.
- Give skills a small, repeatable instruction: inspect/render a CLI-owned template, fill only user-explicit fields, then execute the rendered command when appropriate.
- Preserve omission semantics for prompt mode, TUI/headless posture, managed-header inheritance, profile patching, and similar fields.
- Keep command rendering inspectable and non-executing so agents can show or revise commands before running them.
- Cover the existing `houmao-mgr` command surfaces where system skills currently carry reusable command templates, option-shape menus, or default-sensitive prose: agent definitions, credentials, agent lifecycle, gateway controls, mailbox administration, managed-agent mail fallbacks, and memo seed flags that are already part of profile commands.

**Non-Goals:**

- Replacing Click parsing or turning every `houmao-mgr` command into a templated command.
- Making system skills own project templates, generated config snippets, or default copies of command metadata.
- Executing commands through the renderer.
- Migrating stored project data or changing existing default resolution behavior outside the rendered intent path.
- Moving skill-native loop execplan scaffolds, workspace layout scaffolds, semantic mail/reply prompts, tours, or advanced pattern examples into `houmao-mgr`.

## Scope Boundary

The extraction boundary is command ownership: a template belongs in this change only when it renders, validates, or documents an existing `houmao-mgr` command invocation. Skills may still own prompts, scaffold files, workflow examples, and semantic process documents that are not already represented by a `houmao-mgr` command family.

In scope:

- Agent-definition commands: easy specialists, easy profiles, easy instance launch, low-level roles, recipes, and recipe-backed launch profiles.
- Credential commands: project and plain agent-definition credential add/set/login/list/get/rename/remove for Claude, Codex, and Gemini, including tool-specific option shapes.
- Agent lifecycle commands: launch, launch-profile launch, join, relaunch, cleanup session, and cleanup logs.
- Gateway commands: gateway discovery/control/TUI helpers, mail notifier status/enable/disable, and reminders list/get/create/set/remove.
- Mailbox commands: shared mailbox, project mailbox, project mailbox accounts/messages, and managed-agent mailbox binding commands.
- Managed-agent mail fallback commands under `houmao-mgr agents mail ...`.
- Memo seed flags only where they are part of easy profile or raw launch-profile command templates.

Out of scope:

- `houmao-agent-loop-pro` and `houmao-agent-loop-lite` execplan/intention scaffolds and prepared-agent summary tables.
- `houmao-utils-workspace-mgr` workspace layout scaffolds and ownership plans.
- Semantic workflow prompts such as reply-hardening reminders and process-email heuristics.
- Tours, advanced usage patterns, and compatibility wrappers that do not own a distinct `houmao-mgr` command shape.

## Decisions

### Use CLI-owned templates under `houmao-mgr internals command-templates`

The renderer will live under a new internal command family:

- `houmao-mgr --print-json internals command-templates list`
- `houmao-mgr --print-json internals command-templates show --id <template-id>`
- `houmao-mgr --print-json internals command-templates render --id <template-id> --intent <intent.json>`

This keeps template discovery beside other agent-oriented internal helpers while avoiding a public promise that the template schema is stable for third-party integrations. The command family name is explicit enough that skills can route to it without reading broad CLI docs.

The registry should support both concrete template ids and small template families. Concrete ids are useful for default-sensitive authoring such as `project.easy.profile.create`; family ids are useful for repeated command shapes such as `credentials.<tool>.<verb>` where the tool lane supplies a bounded option menu.

Alternative considered: store Markdown templates inside each system skill. That keeps skill files self-contained, but it recreates the drift problem and makes every default fix a multi-skill documentation patch.

### Represent templates as structured metadata, not freeform Markdown

Each template will be a Python-owned registry entry with a stable id, target argv prefix, operation kind, required fields, optional fields, field-to-option mapping, repeatability, value type, omit semantics, clear semantics, conflicts, conditional requirements, and explanatory notes.

Fields will carry default actions such as `required`, `set-if-supplied`, `omit-to-inherit`, `clear-only`, and `conditional`. Prompt mode and launch posture will be explicit `omit-to-inherit` fields unless the user supplies them or a command-specific rule requires a different treatment.

Alternative considered: render from command help text. Help text is useful for humans but too lossy for conflict handling, clear flags, conditional defaults, and stable machine output.

### Render sparse JSON intent into argv without execution

`render` will accept a small JSON intent object containing a `fields` mapping plus optional context such as project root or known tool lane. It will return structured output with at least:

- `template_id`
- `argv`
- `command`
- `normalized_intent`
- `omitted_fields`
- `applied_fields`
- `warnings`
- `blockers`

When blockers exist, the output will explain them and omit executable argv. The renderer will not call the target command. Skills remain responsible for deciding whether to run the returned argv, ask the user, or report the proposed command.

Alternative considered: add `--dry-run-command` to every target surface. That spreads template logic across many commands and still makes skills know which dry-run shape belongs to each workflow.

### Keep the registry near command definitions and test it like CLI behavior

The implementation should place the registry in the CLI/control layer close to the existing project command definitions rather than inside skill assets. The registry should be small data plus rendering code, with tests that pin the output for default-sensitive fields.

The first implementation can duplicate a small amount of option metadata from Click commands, but the tests must make drift visible. A later refactor can derive more metadata from the command declarations if that becomes valuable.

Template metadata should be organized by command family so non-command skill artifacts do not leak into the registry. Suggested internal namespaces:

- `project.easy.*`
- `project.agents.roles.*`
- `project.agents.recipes.*`
- `project.agents.launch-profiles.*`
- `credentials.*`
- `agents.lifecycle.*`
- `agents.gateway.*`
- `agents.mail.*`
- `mailbox.*`
- `project.mailbox.*`
- `agents.mailbox.*`

### Teach skills to call templates, not to own templates

Packaged skills should contain concise workflow text: resolve `houmao-mgr`, choose the matching template id, render intent with only explicit user/request fields, inspect blockers/warnings, then run or present the rendered argv. Skills may name the important omission rules, but they should not carry full command skeletons with defaulted optional flags.

Skills that are mainly wrappers or examples should not gain extra template text. For example, `houmao-specialist-mgr` should route to the agent-definition template workflow instead of growing its own specialist command skeletons, and loop/workspace skills should keep their scaffold templates because those artifacts are skill-owned rather than `houmao-mgr` command-owned.

## Risks / Trade-offs

- Registry drift from Click option definitions -> Keep the first registry small, add unit tests for every supported template id, and include smoke tests that feed rendered argv into existing command parsers where practical.
- Renderer schema becoming a public API too early -> Place it under `internals`, document it for packaged skills, and avoid compatibility promises beyond in-repo system skills.
- Agents overusing `render` for unsupported commands -> `list` and `show` must make supported ids explicit, and skills must fall back to ordinary CLI help only when no template exists.
- Context-sensitive defaults may need project inspection -> Keep render non-executing and explicit: when the renderer cannot know a stored profile’s tool lane or existing patch state, it reports an explanatory warning rather than guessing.
- More ceremony in simple skill workflows -> The renderer is mostly for create/set/launch authoring; read-only list/get/remove flows can continue using direct command guidance.
