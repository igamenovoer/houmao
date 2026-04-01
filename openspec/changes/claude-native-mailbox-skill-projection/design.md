## Context

Houmao currently projects runtime-owned mailbox skills under a shared `mailbox/` namespace subtree beneath the tool skill destination. That layout works as a visible file surface for Codex-oriented prompting, but an empirical Claude Code TUI probe showed that Claude only discovers native skills when they are installed as top-level skill directories under the active Claude skill root. In the probe, `CLAUDE_CONFIG_DIR/skills/top-probe/SKILL.md` and project-local `.claude/skills/project-probe/SKILL.md` were discovered by `/skills`, while `CLAUDE_CONFIG_DIR/skills/mailbox/namespaced-probe/SKILL.md` was not.

The important constraint is therefore not the `skills` root itself. Under `CLAUDE_CONFIG_DIR`, top-level `skills/<skill-name>/SKILL.md` is already Claude-native. The failure comes from Houmao's extra `mailbox/` namespace layer.

Claude also has a separate project-local `.claude/skills/` discovery surface, but that project-owned tree should remain distinct from Houmao's isolated runtime home. Houmao should not repurpose the launched workdir's `.claude/` directory as its runtime `CLAUDE_CONFIG_DIR`, because the runtime home also owns mutable Claude state such as `.claude.json`, `settings.json`, `sessions/`, `history.jsonl`, `plugins/`, `cache/`, and trust metadata.

## Goals / Non-Goals

**Goals:**

- Make runtime-owned Houmao mailbox skills natively discoverable and invocable in Claude Code sessions.
- Preserve a clear runtime-owned identity boundary for Houmao mailbox skills without depending on the `mailbox/` namespace for Claude.
- Centralize tool-specific mailbox skill path resolution so prompts, docs, and tests do not hard-code one layout for every tool.
- Keep Houmao runtime-owned Claude state out of the user repo's project-local `.claude/` tree.

**Non-Goals:**

- Redesign the non-Claude mailbox skill layout if it is already acceptable for Codex or Gemini.
- Change mailbox workflow semantics, notifier behavior, or gateway API contracts.
- Introduce parallel compatibility mirrors unless they are required by an explicit migration decision.
- Collapse Claude's isolated runtime home into `<workdir>/.claude`.

## Decisions

### 1. Claude mailbox skills will project as top-level Houmao skill directories

For Claude homes, runtime-owned mailbox skills will project as:

- `skills/houmao-process-emails-via-gateway/SKILL.md`
- `skills/houmao-email-via-agent-gateway/SKILL.md`
- `skills/houmao-email-via-filesystem/SKILL.md`
- `skills/houmao-email-via-stalwart/SKILL.md`

This aligns with Claude's native skill discovery under `CLAUDE_CONFIG_DIR`.

Alternatives considered:

- Keep `skills/mailbox/...` and continue instructing Claude to open files directly.
  Rejected because it does not enable native Claude skill discovery and keeps the system at odds with Claude's own skill UX.
- Dual-project both `skills/<skill>` and `skills/mailbox/<skill>`.
  Rejected for now because it creates duplicate assets, duplicate path contracts, and prompt ambiguity in an unstable development system where a direct contract change is acceptable.

### 1a. Houmao will not use `<workdir>/.claude` as `CLAUDE_CONFIG_DIR`

Houmao will keep `CLAUDE_CONFIG_DIR` as an isolated runtime-owned Claude home. Claude-native mailbox skill discovery for Houmao should therefore come from the runtime home's top-level `skills/<houmao-skill>/` directories rather than from the launched project's `.claude/skills/` tree.

Alternatives considered:

- Set `CLAUDE_CONFIG_DIR=<workdir>/.claude`.
  Rejected because it mixes runtime-owned mutable Claude state with user-owned project-local Claude configuration, pollutes repos with session and trust artifacts, and is unnecessary for native skill discovery.

### 2. Tool-specific mailbox path helpers will own the projection contract

Mailbox projection and prompt generation will use centralized helper logic to derive the primary visible path for each tool rather than assuming `skills/mailbox/...` everywhere.

For Claude, helpers should return top-level Houmao skill paths.
For non-Claude tools, helpers may continue to return the current namespaced mailbox subtree if that remains the chosen contract.

Alternatives considered:

- Scatter `if tool == "claude"` branches through prompt builders and docs.
  Rejected because it would duplicate path logic and make future projection changes brittle.

### 3. Houmao ownership for Claude will be enforced by reserved names, not by a subtree

For Claude, runtime-owned mailbox skills will stay separate from role-authored skills through the reserved `houmao-...` naming contract rather than through the `mailbox/` namespace subtree.

Alternatives considered:

- Preserve separation only through a hidden compatibility subtree.
  Rejected because hidden or secondary trees do not solve native Claude discovery.

## Risks / Trade-offs

- [Prompt/path drift] → Mitigation: route all mailbox skill file-path rendering through shared tool-aware helpers and update prompt-focused tests.
- [Name collision with role-authored skills] → Mitigation: keep the reserved `houmao-...` runtime-owned naming contract and treat those names as Houmao-owned.
- [Docs and demos reflecting old paths] → Mitigation: update mailbox reference docs and Claude demo/runtime assertions in the same change.
- [Accidental writes into project `.claude/`] → Mitigation: keep the runtime-home contract explicit in helpers, specs, and validation coverage.
- [Non-Claude regressions from generalized refactors] → Mitigation: keep the change tool-specific where possible and preserve existing non-Claude layout unless tests justify a broader redesign.

## Migration Plan

1. Update mailbox projection helpers to compute Claude-native top-level mailbox skill paths.
2. Reproject runtime-owned mailbox skills for Claude homes using that layout while keeping `CLAUDE_CONFIG_DIR` isolated from the launched workdir.
3. Update runtime prompts and docs to emit the tool-specific visible path.
4. Update focused tests and Claude demo validation to assert native `/skills` discoverability and absence of runtime-owned writes to project-local `.claude/`.
5. Rebuild or restart affected Claude demo/runtime sessions so they pick up the new projection contract.

## Open Questions

None at proposal time.
