## Context

Houmao-managed agents need a provider-level instruction channel for their effective role/system prompt. Claude and Codex have usable native system-prompt or instruction surfaces, but Kimi's installed CLI exposes no per-launch system-prompt or profile override even though Kimi's internal agent core has a system-prompt concept.

The current fallback, `bootstrap_message`, sends Houmao's role prompt as ordinary chat. That can work for first-turn behavior, but it is not a native standing instruction and it does not give the model a reliable reason to reload the prompt after context compaction. Writing the prompt into `houmao-memo.md` is weaker: without a bootstrap instruction, the agent may never read the memo.

Kimi's default prompt includes a skill listing generated from discovered skill metadata. That creates a narrower but useful bootstrap channel: if Houmao projects a mandatory skill whose metadata says when to open it, the agent can discover the skill at chat-session start and after compaction, then the skill body can tell the agent how to fetch its Houmao system prompt through a supported CLI command.

## Goals / Non-Goals

**Goals:**

- Add a Houmao-owned auto-skill mechanism that is injected by managed launch, not installed by user command.
- Bootstrap managed system prompts for tools that lack native system-prompt support but expose startup-visible skill metadata.
- Keep auto skills separate from installable Houmao system skills and user-selected project/private skills.
- Provide a supported read-only CLI for the current managed agent to retrieve its effective Houmao system prompt.
- Stop using chat bootstrap messages for known skill-visible fallback tools such as Kimi when the auto-skill method applies.
- Make unsupported fallback cases fail clearly instead of silently degrading to ordinary chat.

**Non-Goals:**

- Do not modify provider source code.
- Do not add a user-facing auto-skill install/uninstall command.
- Do not make `houmao-auto-system-prompt` part of the packaged system-skill catalog.
- Do not claim the provider has applied the system prompt merely because Houmao projected the auto skill.
- Do not solve tools that lack both native system-prompt support and startup-visible skill metadata.

## Decisions

### Add an auto-skill asset lane

Houmao will add `src/houmao/agents/assets/auto_skills/houmao-auto-system-prompt/SKILL.md` and a small projection helper separate from the current system-skill catalog. Auto skills are runtime bootstrap assets owned by Houmao, while system skills are installable guidance packages selected through user or managed system-skill policy.

Alternative considered: add the skill to `system_skills`. That would make policy semantics ambiguous because `--no-system-skills` and explicit install/uninstall commands could remove the bootstrap path required for a correct managed launch.

### Use metadata only for invocation, workflow for actions

The auto skill's `description` and `whenToUse` metadata will only state when to open the skill: at chat-session start, after context compaction, after resume/relaunch, and before first substantive work if the Houmao system prompt is not confirmed loaded. The actual commands and behavior will live in a `## Workflow` section inside `SKILL.md`.

This matches skill semantics: provider-visible metadata answers "when should I read this skill?", while the skill body answers "what should I do?".

### Fetch the prompt through `houmao-mgr agents self`

The skill workflow will use:

```bash
houmao-mgr agents self system-prompt show --format text
```

The command will resolve the current managed-agent identity through existing `agents self` session authority and return the effective composed Houmao system prompt. The skill will not read manifests, memo files, or internal runtime paths directly.

Alternative considered: instruct the skill to read manifest files. That would leak internal storage layout into provider instructions and make later manifest changes risky.

### Select auto-skill injection through launch capabilities

Launch policy will distinguish three independent capability facts:

- native system-prompt support,
- provider skill support,
- startup-visible skill metadata support.

Tools with native system-prompt support continue to use native injection. Tools such as Kimi, where the CLI lacks native system-prompt support but the provider prompt lists skills, use `auto_skill_system_prompt`. Tools that lack both fail when a managed role/system prompt is required.

Alternative considered: keep `bootstrap_message` as the general fallback. That leaves the same compaction and chat-authority problem in place.

### Project auto skills with collision protection

Brain construction will project selected auto skills into the same tool-visible skill root used by managed skills, such as `skills/` for Kimi and `.gemini/skills/` for Gemini. Projection will be independent from system-skill selection and will happen before provider start.

The auto-skill name is reserved. If a project, private, or user-selected skill attempts to occupy `houmao-auto-system-prompt`, build should fail clearly instead of allowing shadowing.

### Record provenance without overstating model behavior

Construction provenance and runtime manifests will record that the auto skill was selected and projected, the reason for selection, the destination, and the system-prompt hash or reference used by the self command. The runtime will not mark the prompt as applied unless a later observable signal proves the agent loaded it.

## Risks / Trade-offs

- Skill metadata might be ignored by a provider despite skill support → Gate this fallback on a capability named for startup-visible skill metadata, not generic skill installation.
- Kimi may change skill-list rendering after a version update → Keep the Kimi capability evidence version-scoped in launch policy and validate against local source or live probes.
- The agent may fail to run the workflow despite the mandatory skill trigger → Make identity/debugging tests assert the first-turn behavior and keep provenance wording to `projected`, not `applied`.
- `houmao-mgr` may be unavailable in the provider process environment → Treat that as launch/runtime environment breakage; the skill must fail closed and report that the Houmao system prompt could not be loaded.
- Auto-skill collision handling may reject previously accepted skill names → This is intentional because the reserved bootstrap skill name has runtime authority.

## Migration Plan

Add the auto-skill asset and projection code first, then add the self system-prompt CLI, then switch Kimi and other known skill-visible non-native tools from `bootstrap_message` to `auto_skill_system_prompt`. Existing managed homes are repaired on the next build/rebuild because projection overwrites the reserved Houmao auto-skill path.

Rollback is to remove the capability mapping for `auto_skill_system_prompt` and let affected tools return to the previous `bootstrap_message` path. The asset can remain inert if no launch policy selects it.

## Open Questions

- Should Houmao expose a JSON variant of the self command in the first implementation, or keep only `--format text` plus internal manifest hashes?
- Which provider besides Kimi has enough startup-visible skill metadata evidence to opt into this fallback immediately?
