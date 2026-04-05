## Context

Houmao already packages mailbox-oriented Houmao-owned system skills under `src/houmao/agents/assets/system_skills/` and installs them through the shared installer in `src/houmao/agents/system_skills.py`. The shared installer now needs a flat tool-native path contract so the new `houmao-create-specialist` skill and the mailbox skills all live under top-level Houmao-owned directories in the active skill root.

The new `houmao-create-specialist` skill is not a mailbox skill. It belongs to the project/easy authoring workflow and must describe how an agent should create specialists through `houmao-mgr project easy specialist create`. The skill also needs environment-sensitive command selection because Houmao is typically installed for end users via `uv tool install houmao`, while development workspaces may need `.venv`, `pixi`, or repo-local `uv run` invocation instead.

## Goals / Non-Goals

**Goals:**

- Add a packaged Houmao-owned `houmao-create-specialist` skill with instructions centered on `houmao-mgr project easy specialist create`.
- Make the skill choose the `houmao-mgr` launcher in the required precedence order: `.venv`, Pixi, project-local `uv`, then global uv-tools install.
- Require the skill to recover omitted options from current or recent conversation context when those values are explicit, and otherwise ask the user instead of guessing.
- Keep visible system-skill projection flat and tool-native across Claude, Codex, and Gemini.
- Add regression coverage for catalog resolution, flat projection, and visible installed skill content.

**Non-Goals:**

- Changing the `houmao-mgr project easy specialist create` CLI contract itself.
- Introducing dynamic rule engines or nested catalog metadata beyond what is needed for flat path projection.
- Reworking mailbox skill semantics beyond moving all Houmao-owned skills to the flat visible contract.
- Building a general natural-language parameter extraction framework outside the specific skill instructions.

## Decisions

### Decision: Package `houmao-create-specialist` as a flat top-level asset

The new skill will live at `src/houmao/agents/assets/system_skills/houmao-create-specialist/` while keeping the visible skill name exactly `houmao-create-specialist`.

Rationale:

- the visible skill name stays aligned with the user-facing trigger and catalog key,
- the packaged asset path matches the native top-level layout used by the supported agent tools,
- it keeps logical grouping in the catalog sets instead of in filesystem namespace.

Alternatives considered:

- Put the skill under a mailbox-specific path.
  Rejected because the skill is not mailbox-related and would encode the wrong ownership boundary.

### Decision: Keep visible projection flat across supported tools

The installer will project Houmao-owned skills into the top-level native skill destination for each supported tool: `skills/<houmao-skill>/` for Claude and Codex, `.agents/skills/<houmao-skill>/` for Gemini.

Rationale:

- it matches the native loader contract used by Claude Code and Gemini CLI,
- it avoids a Codex-only namespace special case,
- it keeps the reserved `houmao-` skill name as the collision boundary instead of adding a second path segment.

Alternatives considered:

- Keep a Codex-only visible namespace derived from `asset_subpath`.
  Rejected because it would make the shared installer encode a non-portable filesystem contract.

### Decision: Auto-install the new skill through a dedicated `project-easy` set

The catalog will add a new named set, `project-easy`, that contains `houmao-create-specialist`. Managed launch, managed join, and CLI default installation will include both `mailbox-full` and `project-easy`.

Rationale:

- the new skill is intended as a default Houmao-owned workflow aid rather than a hidden optional extra,
- a dedicated set keeps mailbox and project/easy authoring concerns separate while still allowing explicit selection,
- it preserves the set-based catalog model rather than appending the skill ad hoc in code.

Alternatives considered:

- Add the skill directly into `mailbox-full`.
  Rejected because that set name would become misleading.
- Leave the skill manual-only.
  Rejected because the request is to add a Houmao-owned system skill for agents, and manual-only installation would make the default managed experience inconsistent.

### Decision: Encode launcher selection and missing-input policy in the skill text

`houmao-create-specialist` will instruct the agent to detect the correct `houmao-mgr` launcher in this order:

1. `.venv/bin/houmao-mgr`
2. `pixi run houmao-mgr`
3. `uv run houmao-mgr`
4. globally installed `houmao-mgr` from uv tools

The skill will treat current prompt context as the first source of user intent, recent chat context as a second source, and explicit user follow-up questions as the last step when required information remains unresolved. It will use CLI defaults such as `<name>-creds` only when they are documented command defaults, not as guessed user intent.

Rationale:

- the user explicitly requested this precedence and ask-before-guess posture,
- the skill text is the right place to encode conversation-time behavior that the CLI does not enforce,
- it keeps the underlying `houmao-mgr` contract unchanged while guiding the agent toward predictable behavior.

Alternatives considered:

- Hard-code `pixi run houmao-mgr` in the skill.
  Rejected because installed system skills are end-user content and current tests already reject developer-only `pixi run` wording as the ordinary visible contract.
- Treat missing auth as optional and let the CLI fail.
  Rejected because the request is to ask the user instead of guessing when necessary options cannot be established.

## Risks / Trade-offs

- [Flat projection changes the current Codex visible skill paths] → Update docs and tests in the same change and treat stale family-path references as bugs.
- [Default auto-install broadens the Houmao-owned skill surface] → Isolate the new skill in a dedicated `project-easy` set and update inventory tests and docs accordingly.
- [Skill text may drift from the CLI contract] → Anchor the skill wording to the current `project easy specialist create --help` behavior and add assertions for the most important guardrails.
- [Conversation-context recovery can overreach] → Restrict recovery to values explicitly present in the current or recent conversation and instruct the agent to ask when the value remains ambiguous.

## Migration Plan

1. Add the new `houmao-create-specialist` packaged skill asset and catalog entry under the flat asset root.
2. Keep system-skill path projection flat and tool-native across all supported tools.
3. Extend default set selection and test coverage to include the new `project-easy` set.
4. Update any affected docs or inventory descriptions that still say the packaged Houmao-owned skill surface is mailbox-only.
5. Validate the installed skill content locally and with one Claude Code run that reviews the resulting skill behavior.

## Open Questions

- None. The required command-resolution order and missing-input posture were specified directly in the request.
