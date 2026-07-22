## Context

`README.md` (246 lines) is the project's front door. A style audit found:

- Eight or more undefined concepts in the "What It Is" paragraph (`managed agent`, `gateway sidecar`, `mailbox identity`, `turn evidence`, `system-skill installation target`); the Core Concepts table that defines them sits ~100 lines later.
- A Quick Start that interleaves the preferred `npx skills add` path with pinned-tag and four `houmao-mgr system-skills` variants before the reader knows what a pack is, and that ends at "invoke the tour" with no picture of success.
- A System Skills section (lines 154–196) of dense internal prose — pack membership, implicit vs explicit roots, actor entrypoint selection, ownership config, compatibility aliases — with single sentences up to ~110 words. This directly violates the existing `readme-structure` spec requirement that the section be "a concise summary … not a table of protected routines" linked out to the System Skills Overview.
- No prerequisites statement, no license mention, a bare uncaptioned video URL, and unexplained `$houmao-*` invocation syntax.

A follow-up design-choice exploration (`explore/design-choice/design-readme-narrative-sections.md`, decisions D1–D5) then resolved the narrative direction: the name/metaphor, design rationale, and architecture sections are **expanded**, not trimmed; the expansion sits **before Quick Start**; Quick Start becomes a complete zero-to-first-agent arc; architecture teaches both the system view and a single agent's anatomy; and the name/metaphor is **brand identity**, never a teaching device or vocabulary source.

Constraints:

- The `readme-structure` spec (`openspec/specs/readme-structure/spec.md`) mandates the section ordering; the revision keeps that order and modifies the spec where it is stale or contradicts D1–D5 (the ~20-line intro cap).
- External docs and the published site link to README anchors; section titles in the mandated order should keep recognizable names.
- The repo's agent-style ruleset (split sentences over 30 words, plain English, concrete terms) applies to the rewrite.
- System Skills detail moved out of the README has a natural home: `docs/getting-started/system-skills-overview.md` already exists and is the linked target.

## Goals / Non-Goals

**Goals:**

- The README stands alone as a teaching document: brand story, rationale paragraphs, and an architecture walkthrough (system view + single-agent anatomy diagram) appear before Quick Start in scannable subheaded form.
- A newcomer can read top-to-bottom without meeting an undefined load-bearing term; canonical vocabulary (`specialist`, `managed agent`, …) is never shadowed by metaphor language.
- Quick Start is one golden path with per-step expected outcomes and the first `You:`/`AI:` exchange inline; `$houmao-admin-welcome start-guided-tour` is taught as the single skill to remember.
- System Skills section shrinks to its spec-mandated concise summary; detail moves to the overview guide.
- No sentence over ~30 words survives the rewrite; jargon nouns (`posture`, `surface` as a noun, `credential lane`, `pack closure`) are replaced or defined.
- Prerequisites, license, and a captioned demo video are present.
- The `readme-structure` delta spec encodes all of the above as verifiable requirements and refreshes stale text (Kimi Code guidance, tour entrypoint naming, intro cap).

**Non-Goals:**

- No factual re-scoping: nothing true in the current README is deleted, only relocated or reworded.
- No changes to runtime code, CLI surfaces, skills, or tests.
- No redesign of `docs/` structure beyond absorbing the moved System Skills prose.
- No new screenshots or videos; the existing video asset is reused.
- No metaphor-to-concept mapping and no metaphor-derived synonyms: the Wukong story is brand identity only (D5).

## Decisions

- **Story-first structure (D1, D2).** The name-origin brand story, an expanded "Why This Design" rationale, and the architecture walkthrough sit in place before Quick Start. The delta spec replaces the ~20-line intro cap with a ~60-prose-line budget plus required subheadings. Alternative considered: short summary up front with a deep rationale section after the examples — rejected because it quietly recreates the trim-first shape the operator rejected, and splitting the story weakens it.
- **Brand, not curriculum (D5).** The Wukong/metaphor material is written as brand narrative. It gets no mapping block to Houmao concepts, and metaphor words never appear as synonyms for `specialist` or `managed agent`. Alternative considered: metaphor-as-teaching-scaffold — rejected by the operator; the name is a brand name.
- **Architecture teaches two views (D4).** The section narrates the existing team diagram and adds a second mermaid diagram of one managed agent's anatomy (provider CLI in tmux, gateway sidecar, mailbox identity, memory directory). Both diagrams stay conceptual — no CLI syntax. Alternative considered: adding a request-lifecycle walkthrough — rejected as duplicating gateway/TUI-tracking docs with high drift risk.
- **Define-before-use over reorder-everything.** The spec's section order is sound once each section is written plainly. Rather than moving Core Concepts earlier, the rewrite defines each term in one plain clause at first use and keeps the full table as the reference.
- **Golden path plus outcomes (D3).** Quick Start keeps exactly: prerequisites, `uv tool install houmao`, `command -v tmux`, `npx skills add …`, start CLI agent, `$houmao-admin-welcome start-guided-tour` — each with a one-line expected outcome — and closes with the first `You:`/`AI:` exchange inline. Pinned-tag installs, `houmao-mgr system-skills install` variants, explicit homes, and copy-paste installs each get one sentence with a docs link. The separate "Agent-Driven Examples" section keeps the gateway-interaction example to avoid duplication.
- **Welcome-skill primacy (operator directive).** The README frames `$houmao-admin-welcome start-guided-tour` as the one invocation a newcomer must remember, both in Quick Start and in the System Skills section (welcome listed first, labeled as the starting skill).
- **Relocate, don't delete, System Skills prose.** Pack membership rules, actor entrypoint selection, bypass routes, ownership config, and compatibility aliases move into `docs/getting-started/system-skills-overview.md` (merging with what it already covers; deduplicate on overlap). The README keeps the six-skill table, the actor model in one short paragraph, and the link.
- **Sentence-level rewrite with agent-style as the yardstick**: split anything over ~30 words, replace abstraction-nouns with concrete terms, keep the existing tables, mermaid diagrams, and `You:`/`AI:` dialogue examples.
- **Spec delta updates stale text in place**: the Kimi guidance requirement is rewritten to match maintained 0.23.x reality, `houmao-touring` references become `houmao-admin-welcome`, and the intro-cap requirement is replaced by the narrative budget.

## Risks / Trade-offs

- [Story-first delays the first runnable step by ~2 screens] → Accepted trade-off (D2); mitigated by subheadings, the explicit ~60-line budget, and a table of contents if the budget is exceeded.
- [Anchor/link breakage from renamed sections] → Keep the mandated section titles verbatim; verify all `docs/**` links into README anchors still resolve after the rewrite.
- [Moved System Skills prose drifts from the overview doc's existing content] → Merge into the overview's existing sections during implementation; where the README text is newer, prefer it and rewrite the overview passage rather than appending a duplicate block.
- [Readability rules vs. precision loss] → Each split sentence must keep its factual content; review the final diff against the current README line by line to confirm no fact was dropped.
- [Two mermaid diagrams drifting as the runtime evolves] → Keep both diagrams conceptual (no flags, no command text); the anatomy diagram names only durable elements (process, tmux, gateway, mailbox, memory).
- [Spec delta and rewrite disagreeing] → Implement the README rewrite and the delta spec from the same outline; the verify step checks the README against every ADDED/MODIFIED scenario.
- [Over-trimming the System Skills table loses the pack-membership column users install from] → Keep the table as-is (it is the useful part); only the prose after it moves.
