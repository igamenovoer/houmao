## Context

Houmao now supports Kimi Code as a maintained provider in both `kimi_headless` and `local_interactive` paths. The current README and docs already contain detailed Kimi references in some deeper pages, but the most visible onboarding text and several diagrams still use Gemini as the third primary example provider. That creates a mismatch between runtime support and reader-facing guidance.

The local Kimi Code CLI reports version 0.11.0. Its current help output exposes `--skills-dir` but no native system-prompt or append-system-prompt flag, so Kimi Code guidance needs an explicit caveat: `houmao-auto-system-prompt` may need to be invoked manually before substantive chat begins when automatic skill startup does not fire.

The affected surfaces are documentation-only:

- README front-door prose and Architecture at a Glance diagram.
- Getting-started overview and quickstart provider lists and join diagram.
- Build-phase launch-policy reference version wording and Kimi caveats.
- CLI reference, system-skills reference, and system-skills overview provider lists.
- Run-phase backend, launch-plan, role-injection, and session-lifecycle provider-order lists.
- Developer TUI parsing architecture and shared-contract pages that still describe only Claude/Codex TUI parser coverage.

## Goals / Non-Goals

**Goals:**

- Make Kimi Code visible as a primary Houmao provider in the README and docs.
- Use one consistent provider-priority order for launch-capable providers: Claude, Codex, Kimi, then Gemini.
- When a short prose example, graphic, or diagram can list only three providers, list Claude, Codex, and Kimi.
- Warn that Kimi Code 0.11.0 lacks a native system-prompt flag, and that users may need to invoke `houmao-auto-system-prompt` manually before substantive Kimi chat begins.
- Keep Gemini documented as supported where it is actually supported, especially headless and local-interactive backend references.
- Keep Copilot described as a system-skill installation target rather than a launch backend.
- Update docs contracts so future changes do not reintroduce Gemini as the default third example provider.

**Non-Goals:**

- Do not change runtime provider support, launch policy, credential handling, TUI tracking code, or system-skill projection behavior.
- Do not remove Gemini support from docs where the page is listing all maintained providers or explaining Gemini-specific behavior.
- Do not introduce new docs pages unless an existing page cannot represent the provider-priority rule clearly.

## Decisions

### Decision: Use a Documentation Provider Priority Rule

Documentation should follow this rule:

1. Full launch-provider lists use `Claude, Codex, Kimi, Gemini`.
2. Short three-provider lists, graphics, and compact examples use `Claude, Codex, Kimi`.
3. Tool identifiers follow the same priority when represented as CLI values: `claude,codex,kimi` for short examples and `claude,codex,kimi,gemini` for full launch-provider examples.
4. Copilot appears only in system-skill installation contexts unless a page is explicitly about skill installation targets.

Alternative considered: keep all provider lists alphabetical or historical. That would preserve older docs shape, but it does not communicate that Kimi is now one of the primary maintained launch surfaces.

### Decision: Add a Kimi System-Prompt Caveat

Docs should say that Kimi Code 0.11.0 does not expose a native system-prompt flag. Houmao can project `houmao-auto-system-prompt` as a managed auto skill and Kimi can load skills, but automatic startup triggering may not happen before the first user-visible chat turn. The docs should warn Kimi users to manually invoke `houmao-auto-system-prompt` as the first action when the prompt is not confirmed loaded.

Alternative considered: omit the caveat because Kimi supports skills. That would hide the operational gap that skills and native system prompts are different mechanisms.

### Decision: Preserve Backend-Specific Accuracy

Some pages describe backend differences rather than marketing or onboarding priority. Those pages should still mention Gemini when the statement is true, but Kimi should precede Gemini in neutral lists. Gemini-specific sections, validation checklists, and support caveats stay in place.

Alternative considered: replacing Gemini with Kimi everywhere. That would be simpler, but it would incorrectly hide supported Gemini flows and make existing Gemini-specific requirements stale.

### Decision: Update Current Docs and Current Specs Together

The implementation should update both Markdown docs and the affected OpenSpec docs requirements. This keeps `openspec validate --specs --strict` meaningful and prevents the old README/developer-guide contracts from pulling docs back toward stale provider lists.

Alternative considered: only editing Markdown docs. That would satisfy the visible request temporarily, but archived or current specs would remain inconsistent with the new documentation rule.

### Decision: Validate With Targeted Text Search

Because this is a docs-only consistency change, validation should include targeted `rg` checks for stale patterns such as:

- `Claude, Codex, Gemini`
- `claude,codex,gemini`
- `claude, codex, or gemini`
- `Provider parser<br/>Claude or Codex`

These searches should not blindly replace every occurrence. Each match should be classified as either a front-door/short-list drift or a backend-specific accurate Gemini mention.

## Risks / Trade-offs

- Over-replacement could remove accurate Gemini-specific documentation → Mitigate by reviewing each match in context and preserving full-provider or Gemini-specific sections.
- Under-replacement could leave front-door docs implying Gemini is still the third primary provider → Mitigate with targeted text searches before finishing.
- Provider order could become inconsistent between README, getting-started, and reference docs → Mitigate by adding spec requirements for the shared priority rule across the affected docs capabilities.
- The Kimi caveat could be mistaken as lack of Houmao Kimi support → Mitigate by stating the precise gap: Kimi Code 0.11.0 lacks native system-prompt injection, while managed Kimi launches and skill projection remain supported.
