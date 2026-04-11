## Context

Managed launch prompt composition currently treats the managed header as one policy decision: enabled or disabled. When enabled, `render_managed_prompt_header()` returns one text block that mixes identity, Houmao runtime guidance, and general behavioral guidance under a single `<managed_header>` section.

The current launch-profile catalog stores `managed_header_policy` as `inherit|enabled|disabled`, and launch flows pass a one-shot `managed_header_override` boolean through `launch_managed_agent_locally()`. That whole-header policy remains useful and should continue to work. The new need is narrower: make independently meaningful header content addressable as named sections, add automation and task-reminder notices, add an opt-in mail acknowledgement section, and allow section-level policy without forcing operators to lose all managed context.

The automation notice is agent-facing behavioral guidance. It is intentionally independent of provider startup prompt policy. `operator_prompt_mode = as_is` means Houmao does not force unattended startup policy; it does not mean the running managed agent may call Claude's `AskUserQuestion` tool or equivalent interactive user-question tools during task execution.

## Goals / Non-Goals

**Goals:**

- Render the managed header as deterministic named subsections.
- Enable the existing identity, Houmao runtime guidance, and automation notice sections by default whenever the managed header is enabled.
- Add an automation notice that applies to all managed launches, including launches whose provider startup policy is `as_is`.
- Add a task reminder section that is disabled by default and guides potentially long-running work to use one-off live gateway reminders when enabled explicitly.
- Add a mail acknowledgement section that is disabled by default and can be enabled explicitly.
- Preserve `--managed-header` / `--no-managed-header` as whole-header controls.
- Add stored and one-shot section-level controls for launch-profile-backed and direct launch flows.
- Persist secret-free section decision metadata for debug/relaunch inspection.
- Keep the mailbox clarification rule in prompt text clear enough for autonomous agents to follow.
- Keep the task reminder rule scoped to potentially long-running work so short tasks do not create unnecessary reminders.
- Keep the mail acknowledgement rule opt-in so existing managed launches do not start acknowledging mail by default.

**Non-Goals:**

- Do not change provider startup prompt-mode semantics or unattended launch-policy strategy selection.
- Do not add new mail APIs or change mailbox transport behavior.
- Do not remove the existing whole-header policy vocabulary.
- Do not make section controls role- or tool-specific in this change.

## Decisions

### Section Model

Use a closed set of managed-header section identifiers:

- `identity`
- `houmao-runtime-guidance`
- `automation-notice`
- `task-reminder`
- `mail-ack`

The rendered structure should be:

```xml
<houmao_system_prompt version="...">
<managed_header>
<identity>
...
</identity>
<houmao_runtime_guidance>
...
</houmao_runtime_guidance>
<automation_notice>
...
</automation_notice>
<task_reminder>
...
</task_reminder>
<mail_ack>
...
</mail_ack>
</managed_header>
<prompt_body>
...
</prompt_body>
</houmao_system_prompt>
```

Use kebab-case section names for CLI/storage and XML-compatible snake_case tags for rendered prompt sections. This keeps CLI values readable while avoiding hyphens in XML-like tag names.

Alternative considered: store arbitrary section names. Rejected because prompt sections are product-defined and should have stable, testable semantics.

### Defaults and Precedence

Whole-header policy remains the outer gate:

1. one-shot whole-header override,
2. stored whole-header policy,
3. default enabled.

Section policy resolves only when the whole header is enabled:

1. one-shot section override,
2. stored section policy,
3. section default.

Section defaults are explicit per section:

- `identity`: enabled
- `houmao-runtime-guidance`: enabled
- `automation-notice`: enabled
- `task-reminder`: disabled
- `mail-ack`: disabled

The `automation-notice` section remains default-enabled for `operator_prompt_mode = as_is`. `as_is` remains provider-startup policy only. The `task-reminder` and `mail-ack` sections remain default-disabled even when the whole managed header is enabled.

Alternative considered: derive `automation-notice` from `operator_prompt_mode = unattended`. Rejected because the desired rule is agent-facing automation guidance for all managed agents, not only provider startup prompt suppression.

### Automation Notice Text

The automation notice should be direct and use uppercase only for the prohibition:

```text
You are running in fully automated mode.

DO NOT call Claude's AskUserQuestion tool. DO NOT use any equivalent interactive user-question tool that would open or focus an operator TUI panel.

Make decisions on your own with available context, including when clarification is unavailable.

For mailbox-driven work, DO NOT ask the interactive operator for clarification. If the relevant mailbox thread is reply-enabled, reply to that thread with a focused clarification question. If the thread is not reply-enabled, decide on your own with available context. This applies both when the ambiguity is in the message itself and when it appears while carrying out work requested by that message. Treat the mailbox sender as the likely upstream coordinator, often another agent.
```

This wording intentionally names Claude's built-in `AskUserQuestion` tool while also covering equivalent user-question tools in other frontends.

### Task Reminder Text

The task reminder section should be direct and identify the supported gateway reminder surface:

```text
When starting potentially long-running work, such as processing email, create a one-off reminder on the live gateway to remind yourself to verify final output actions are complete before finishing. Use a default notification check delay of 10 seconds. The reminder should name the expected final action, such as replying to mail or writing a required file. Delete or otherwise turn off that reminder when the task is done.
```

This section does not add a new reminder API. It points agents at the existing live gateway reminder surface. The reminder is one-off live gateway state, not a durable recovery queue, and should be cancelled once the task's completion conditions have been satisfied.

### Mail Acknowledgement Text

The mail acknowledgement section should be concise and opt-in:

```text
For mailbox-driven work, always send a concise acknowledgement to the reply-enabled address before doing substantive work.
```

The section only instructs acknowledgement when a reply-enabled address exists. It does not make non-reply-enabled operator-origin mail replyable, and it does not override the automation notice's instruction to decide autonomously when clarification is unavailable.

### CLI Shape

Keep current flags:

- `--managed-header`
- `--no-managed-header`
- `--clear-managed-header` where stored profile mutation supports it

Add repeatable section policy flags:

- stored profile create/set: `--managed-header-section <section>=enabled|disabled`
- stored profile set: `--clear-managed-header-section <section>`
- stored profile set: `--clear-managed-header-sections`
- one-shot launches: `--managed-header-section <section>=enabled|disabled`

Using one repeatable `SECTION=STATE` option avoids adding two flags per section and makes future section additions cheaper. Unsupported section names and unsupported states should fail with Click errors before launch.

### Storage and Payloads

Store section policy as a small JSON mapping on launch profiles, for example:

```json
{
  "identity": "enabled",
  "automation-notice": "disabled",
  "task-reminder": "disabled",
  "mail-ack": "enabled"
}
```

Omitted section keys mean inherit/default, not disabled. Existing profiles with no section-policy column or no mapping keep default-enabled sections enabled and keep default-disabled sections disabled.

Payloads should expose a secret-free `managed_header_sections` mapping or list that distinguishes stored policy from resolved launch-time decisions where needed. Existing `managed_header` payloads should remain present for whole-header policy.

### Launch Metadata

Managed prompt metadata should record:

- whole-header enabled/disabled decision and resolution source,
- stored whole-header policy,
- resolved section decisions,
- section decision source per section,
- rendered layout metadata with section tags.

Relaunch from old manifests should continue to recompute missing metadata with current per-section defaults. Existing whole-header disable metadata must still suppress the whole header even though most sections default to enabled.

## Risks / Trade-offs

- **Risk:** Section policy storage adds another catalog migration surface. → **Mitigation:** Use additive nullable JSON storage with missing values treated as section defaults.
- **Risk:** The automation notice could conflict with interactive debugging expectations. → **Mitigation:** Keep whole-header and section-level disable controls; make `as_is` semantics explicit as provider-startup-only.
- **Risk:** Prompt text becomes too large or noisy. → **Mitigation:** Keep sections concise and deterministic; allow section-level opt-out.
- **Risk:** CLI shape becomes verbose. → **Mitigation:** Use repeatable `--managed-header-section SECTION=STATE` rather than separate flags for every section.
- **Risk:** Mailbox clarification guidance may be misapplied outside mailbox-driven work. → **Mitigation:** Scope the mailbox rule explicitly to mailbox-driven work and the relevant mailbox thread.

## Migration Plan

1. Add section model types, default resolution, and rendering helpers.
2. Add additive catalog storage for stored launch-profile section policy.
3. Thread stored and one-shot section policy through launch-profile and easy-profile launch flows.
4. Extend managed prompt metadata with section decisions.
5. Update docs and tests.

Rollback can ignore the new stored section-policy column/mapping and continue using the whole-header policy. Existing profiles remain valid because missing section policy means each section uses its defined default.
