## Context

The maintained launch implementation resolves omitted headless posture as local interactive/TUI when the tool supports that backend. Easy profile and raw launch-profile storage only persist `headless: true` when `--headless` is explicitly supplied, and easy/profile launch falls back to non-headless unless the stored posture or direct launch flags request headless. Gemini remains an exception because the current easy-launch surface requires headless for Gemini specialists.

The packaged system skills mention `--headless` as an available option, but they do not consistently teach agents what to do when the user omits launch posture. The ambiguous wording is enough for agents to store or pass `--headless` even though the default CLI behavior would have launched a TUI-backed agent.

## Goals / Non-Goals

**Goals:**

- Make TUI/local interactive the explicit system-skill default for profile creation and launch invocation when the selected tool supports it.
- Tell agents to add `--headless` only when the user explicitly requests it or the selected tool/lane requires it.
- Keep prompt mode (`unattended` versus `as_is`) distinct from TUI/headless launch posture.
- Preserve existing Gemini headless-only guidance.

**Non-Goals:**

- Change CLI behavior, runtime backend selection, database storage, or launch-profile schema.
- Add new launch flags.
- Change gateway foreground/background defaults.
- Redesign profile lanes or specialist authoring.

## Decisions

1. Treat this as skill text and spec work only.

   The runtime already behaves correctly: absent `headless` storage resolves as non-headless, and non-headless launch selects the local interactive backend when available. Changing implementation would risk creating a second defaulting source with no behavioral benefit.

   Alternative considered: add CLI warnings or new default fields. Rejected because the issue is agent instruction ambiguity, not operator CLI semantics.

2. Add shared defaulting guidance close to the relevant subskill/action pages.

   The affected agent decisions happen in `houmao-agent-definition` profile authoring, create-agent-fast-forward, easy launch, and `houmao-agent-instance` launch guidance. Updating these pages keeps the instruction near command construction and avoids making the top-level routers too dense.

   Alternative considered: add only a top-level note. Rejected because agents often load the route page for the concrete action, and command-specific guardrails need to be visible there.

3. Separate prompt mode from launch posture explicitly.

   `unattended` is a prompt/provider startup posture; it does not imply headless. The revised guidance should continue to allow unattended prompt-mode defaults where already required while preventing agents from translating that into `--headless`.

   Alternative considered: remove unattended defaults from fast-forward guidance. Rejected because existing ready-profile behavior intentionally defaults prompt mode to unattended unless the user asks for `as_is`.

## Risks / Trade-offs

- Agents may still confuse "unattended" with "headless" if only one page is updated -> Mitigation: update both definition and instance launch guidance, plus the ready-profile workflow spec.
- The phrase "if supported" could be underspecified for agents -> Mitigation: name Gemini as the known headless-only exception and say not to infer other headless requirements unless the skill, CLI, or selected tool contract says so.
- Future tools may support only headless or only TUI -> Mitigation: phrase the default as "prefer TUI/local interactive when supported" and allow required-headless exceptions.
