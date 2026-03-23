## Context

The mailbox runtime already projects mailbox system skills into the active skill destination for mailbox-enabled homes, and a recent fix started mirroring those skills into a visible `skills/mailbox/...` subtree because Codex does not treat hidden `.system` entries as a safe ordinary discovery surface. That partial fix solved the demo-pack pathing problem, but the generic runtime `mail` prompt path, several focused tests, and the mailbox reference docs still describe `.system/mailbox/...` as the primary contract.

This change is cross-cutting but narrow. It touches runtime mailbox skill projection, runtime-owned `mail` prompt construction, and the docs/tests that define or verify those behaviors. It does not change gateway mail APIs, mailbox transport semantics, or the role of mailbox env bindings.

Two tool constraints matter:

- Codex-compatible prompting cannot rely on hidden-dot mailbox skill discovery, because `.system` is a reserved cache-style area rather than the stable ordinary discovery surface.
- Regular headless Claude runs can resolve a custom skill by name from `<config-home>/skills`, so Claude-compatible homes do not need a hidden-path workaround as their primary contract.

## Goals / Non-Goals

**Goals:**

- Make the visible mailbox skill projection under the active skill destination the primary runtime mailbox skill contract.
- Keep a hidden mailbox-skill mirror only as a compatibility surface where the runtime still benefits from it.
- Update runtime-owned `mail` prompt construction so it points agents at a discoverable mailbox skill surface rather than a hidden-only mailbox path.
- Bring mailbox reference docs and focused tests back into sync with the intended runtime contract.

**Non-Goals:**

- Removing the hidden `.system` mailbox mirror entirely in this change.
- Redesigning generic skill projection for non-mailbox skills.
- Changing mailbox transport behavior, gateway routes, or mailbox env-binding semantics.
- Reworking demo-pack prompting beyond whatever naturally falls out of the shared runtime mailbox contract updates.

## Decisions

### Decision: The visible mailbox subtree is the normative runtime mailbox skill surface

The runtime will treat the non-hidden mailbox subtree under the active skill destination as the normative mailbox skill surface for ordinary discovery and prompting. For the current adapters, that means `skills/mailbox/...` is the primary contract.

The hidden `.system/mailbox/...` copy remains allowed as a compatibility mirror, but it is no longer the main mailbox skill namespace described by prompts, tests, or docs.

Alternatives considered:

- Keep `.system/mailbox/...` as the normative contract: rejected because it preserves the Codex discovery bug in non-demo `mail` flows.
- Remove `.system/mailbox/...` immediately: rejected because the mirror is still useful as a compatibility surface and there is no need to force that cleanup into the same change.

### Decision: Runtime `mail` prompts identify both the stable mailbox skill name and the visible primary path

The runtime-owned `mail` prompt will identify the transport-specific mailbox skill in a tool-safe way: it will name the skill and point to the primary visible mailbox skill document under the active skill destination.

This keeps the prompt safe for Codex, which can open the visible path directly, while remaining compatible with Claude homes, where the same projected skill also lives under `<config-home>/skills` and can be resolved by name in ordinary headless mode.

The hidden mirror may be mentioned only as compatibility context or fallback, never as the sole primary mailbox-skill reference.

Alternatives considered:

- Use only the skill name: rejected because path-based discovery remains the more conservative cross-tool surface, especially for Codex-managed flows.
- Use only the visible file path: rejected because the stable skill name is still valuable documentation and works with Claude’s ordinary skill resolution model.
- Continue using only the hidden path: rejected because it is the current bug.

### Decision: Contract docs and focused tests update in the same change

The docs and focused tests that currently assert hidden `.system/mailbox/...` as the primary path will be updated together with the runtime helpers and prompt construction.

This keeps the synced spec, repo docs, and targeted verification aligned on one runtime contract instead of carrying the visible-path implementation under a hidden-path narrative.

Alternatives considered:

- Fix code first and defer docs/tests: rejected because the hidden-path contract would remain encoded in both tests and user-facing reference material.
- Treat the docs as pure implementation fallout with no spec delta: rejected because the mailbox docs currently make normative statements about runtime skill projection and mail-command expectations.

## Risks / Trade-offs

- [Visible and hidden mailbox projections can drift] → Keep both trees generated from the same packaged mailbox skill source and centralize prompt/reference helpers so there is one contract to update.
- [Prompt wording becomes slightly longer] → Accept the extra text because it buys cross-tool clarity and removes a real runtime failure mode.
- [Tool discovery behavior may evolve upstream] → Keep the primary contract anchored on the visible projected path and stable skill name instead of one tool’s hidden-cache behavior.

## Migration Plan

No data migration or operator migration is required.

Implementation rollout is code-and-docs only:

1. Update mailbox skill reference helpers so the visible mailbox subtree is the primary mailbox skill surface.
2. Update runtime `mail` prompt construction and focused tests to use the new discoverable mailbox skill contract.
3. Refresh mailbox reference docs so quickstart, contract, and internal pages describe the visible mailbox skill surface and compatibility-mirror semantics consistently.

Rollback is a normal code revert of the helper, prompt, tests, and docs together.

## Open Questions

- None. The scope is narrow and the discovery behavior needed for Codex and ordinary headless Claude runs is already clear enough to implement.
