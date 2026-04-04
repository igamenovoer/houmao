## Why

The `docs/` tree was last substantially refreshed on March 31, 2026, but several significant features shipped after that date (gateway mail-notifier revisions, native project mailbox skills for Claude, project-aware operations) and multiple CLI reference pages were left as truncated stubs during the prior doc pass. Operators working from the current docs will hit gaps on mail-notifier configuration, project-aware command behavior, and several CLI subcommand pages that cut off mid-content.

## What Changes

- **Complete truncated CLI reference pages**: `agents-gateway.md`, `agents-mail.md`, `agents-mailbox.md`, `agents-turn.md` — fill in all missing subcommand sections with option tables and usage notes.
- **Rewrite `houmao-passive-server.md`**: expand from 30-line stub to a proper reference covering when/why to use it, API contract, comparison with `houmao-server`, and operational guidance.
- **Add gateway mail-notifier conceptual doc**: explain what it does, how it integrates with the gateway lifecycle, email processing prompt flow, and `enable`/`disable`/`status` configuration.
- **Document project-aware operations**: explain how commands now resolve against the active project overlay automatically, including `HOUMAO_PROJECT_DIR` override and the catalog-backed overlay storage model.
- **Document project mailbox skills for Claude**: explain native mailbox skill projection added in `b362772`, when it activates, and what it provides to agents.
- **Add easy-specialist conceptual guide**: explain the mental model — when to use `project easy specialist` vs full role/preset definitions, and how instances relate to managed agents.
- **Document launch policy engine**: cover `agents/launch_policy/` — policy models, `OperatorPromptMode`, provider hooks, and the versioned registry.
- **Polish quickstart**: ensure both workflows (join existing session, build from `.houmao/` overlay) are complete end-to-end with no truncation.
- **Housekeeping**: grep `docs/` for stale "agentsys" references and replace with "houmao"; verify all cross-references resolve; update `index.md` and `reference/index.md` with new pages.

## Capabilities

### New Capabilities

- `docs-gateway-mail-notifier-reference`: Reference documentation for the gateway mail-notifier subsystem — what it is, configuration, email processing flow, CLI commands.
- `docs-project-aware-operations`: Documentation for project-aware command resolution — how commands resolve the active project overlay, environment overrides, catalog-backed storage.
- `docs-project-mailbox-skills`: Documentation for native project mailbox skill projection for Claude — when it activates, what skills are injected, how it works with the build phase.
- `docs-easy-specialist-guide`: Conceptual guide for the easy-specialist/instance model — when to use it, how it relates to full presets, lifecycle.
- `docs-launch-policy-reference`: Reference documentation for the launch policy engine — policy models, operator prompt modes, provider hooks, versioned registry.

### Modified Capabilities

- `docs-cli-reference`: Complete the truncated CLI subcommand pages (agents-gateway, agents-mail, agents-mailbox, agents-turn) and rewrite houmao-passive-server reference.
- `docs-getting-started`: Polish quickstart to complete both workflows end-to-end; add easy-specialist guidance.
- `docs-site-structure`: Update index pages to link new docs; verify cross-references.
- `docs-stale-content-removal`: Sweep "agentsys" references from all docs.

## Impact

- **Files modified**: ~15 existing docs pages updated or completed, ~5 new pages created.
- **Code**: Zero code changes — this is a docs-only change.
- **Dependencies**: None. Content is derived from current source code, CLI help output, and module docstrings.
- **Systems**: No runtime impact. Documentation site will have expanded coverage.
