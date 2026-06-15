## Why

Kimi Code is now a maintained Houmao provider for headless and local-interactive managed agents, but the README and several docs pages still present Gemini as the third primary provider. This makes front-door guidance and provider diagrams lag the current supported-provider posture.

## What Changes

- Update project README guidance and diagrams so Kimi is treated as a primary launch-capable provider alongside Claude and Codex.
- Apply a consistent provider-priority rule across docs: use `Claude, Codex, Kimi, Gemini` when listing all maintained launch providers, and use only `Claude, Codex, Kimi` when a short example or graphic has room for three providers.
- Add a version-scoped warning that Kimi Code 0.11.0 does not expose a native system-prompt flag, so Kimi Code users may need to invoke `houmao-auto-system-prompt` manually before substantive chat begins.
- Keep Gemini documented as supported where it is actually supported, but lower its narrative priority behind Kimi.
- Keep Copilot clearly scoped as a system-skill installation target rather than a launch backend.
- Refresh TUI/developer diagrams and prose that still imply only Claude and Codex have maintained TUI tracking, so Kimi Code support is visible in the current architecture.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `readme-structure`: README provider examples and diagrams must prioritize Kimi over Gemini and keep Copilot scoped to system-skill installation.
- `docs-getting-started`: getting-started overview, quickstart, and related onboarding pages must mention Kimi Code as a primary supported provider and follow the provider-priority rule.
- `docs-build-phase-reference`: build-phase launch-policy references must use the current Kimi Code 0.11.0 caveat for missing native system-prompt support.
- `docs-cli-reference`: CLI and system-skills references must include Kimi in provider lists and use the provider-priority rule in examples and summaries.
- `docs-system-skills-overview-guide`: system-skills overview install examples and provider target lists must place Kimi ahead of Gemini while keeping Copilot scoped to skill installation.
- `docs-run-phase-reference`: run-phase backend, launch-plan, role-injection, and lifecycle references must present Kimi before Gemini in provider lists while preserving accurate backend-specific behavior.
- `docs-developer-guides`: TUI parsing developer docs and diagrams must include Kimi Code as a maintained TUI-tracked provider and clarify Gemini's lower-priority/headless-oriented posture.

## Impact

- Affected docs: `README.md` and Markdown pages under `docs/`, especially getting-started, build-phase reference, CLI reference, run-phase reference, mailbox/system-skills references, and developer TUI parsing docs.
- No runtime code, public CLI behavior, schema, or dependency changes are expected.
- Validation should include docs text search for stale three-provider lists that mention Gemini instead of Kimi, plus normal formatting/lint checks if docs tooling requires them.
