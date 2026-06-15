## 1. README Provider Priority

- [x] 1.1 Update `README.md` front-door provider prose so compact launch-provider lists use Claude, Codex, and Kimi, with full launch-provider lists ordered Claude, Codex, Kimi, then Gemini.
- [x] 1.2 Update the README Architecture at a Glance Mermaid diagram so its three visible provider examples are Claude, Codex, and Kimi.
- [x] 1.3 Update README quick command examples, use cases, and demo descriptions so short examples use `claude,codex,kimi` and Copilot only appears in system-skill installation contexts.
- [x] 1.4 Add a README Kimi Code warning naming version 0.11.0 and explaining that users may need to invoke `houmao-auto-system-prompt` manually before substantive Kimi chat begins because Kimi Code lacks a native system-prompt flag.

## 2. Getting-Started Docs

- [x] 2.1 Update `docs/getting-started/overview.md` to name Kimi Code as a primary provider and place Kimi before Gemini in neutral provider lists.
- [x] 2.2 Update `docs/getting-started/quickstart.md` opening prose, command examples, and provider adoption sequence diagram so compact provider examples use Claude, Codex, and Kimi.
- [x] 2.3 Add the Kimi Code 0.11.0 system-prompt warning to the Kimi-aware getting-started guidance, including quickstart or overview text.
- [x] 2.4 Review other `docs/getting-started/` pages for stale short provider lists and update them to follow the provider-priority rule without removing accurate Gemini-specific guidance.

## 3. CLI and System-Skills References

- [x] 3.1 Update CLI reference pages under `docs/reference/cli/` and `docs/reference/cli.md` so neutral launch-provider lists order providers as Claude, Codex, Kimi, then Gemini.
- [x] 3.2 Update system-skill installation target prose and examples in CLI references so launch-capable tools appear before Copilot and short examples use `claude,codex,kimi`.
- [x] 3.3 Update credential and internals references so Kimi stays visible in supported CRUD lanes while login-helper caveats remain accurate for Claude, Codex, and Gemini.
- [x] 3.4 Update `docs/getting-started/system-skills-overview.md` Kimi reachability guidance with the Kimi Code 0.11.0 `houmao-auto-system-prompt` manual-invocation warning.

## 4. Build-Phase, Run-Phase, and Runtime References

- [x] 4.1 Update `docs/reference/build-phase/launch-policy.md` so current Kimi launch behavior is versioned to Kimi Code 0.11.0 and includes the native system-prompt caveat.
- [x] 4.2 Update run-phase reference pages for backends, launch plans, role injection, and session lifecycle so neutral provider lists place Kimi before Gemini.
- [x] 4.3 Add the Kimi Code 0.11.0 native system-prompt warning to Kimi role-injection or backend reference text without claiming Kimi launch or skill projection is unsupported.
- [x] 4.4 Preserve Gemini-specific backend, validation, and relaunch caveats while replacing only short or neutral examples that incorrectly make Gemini the third primary provider.
- [x] 4.5 Review related runtime reference docs, including realm controller and mailbox pages, for provider-order drift and update only documentation affected by the Kimi-priority rule.

## 5. Developer TUI Parsing Docs

- [x] 5.1 Update `docs/developer/tui-parsing/architecture.md` diagrams and prose so maintained local-interactive TUI tracking coverage includes Claude Code, Codex, and Kimi Code.
- [x] 5.2 Update the TUI parsing index page with a provider note that Kimi has maintained local-interactive TUI tracking coverage and Gemini remains outside that maintained TUI tracking path by default.
- [x] 5.3 Update shared-contracts TUI parsing docs to distinguish Claude and Codex legacy parser subclasses from Kimi's dedicated shared-tracker detector profile.

## 6. Spec Synchronization and Validation

- [x] 6.1 Update current OpenSpec docs requirements for the affected capabilities so they encode the Kimi-priority provider rule and Copilot scope.
- [x] 6.2 Run targeted `rg` checks for stale short-list patterns such as `Claude, Codex, Gemini`, `claude,codex,gemini`, `claude, codex, or gemini`, `Provider parser<br/>Claude or Codex`, and stale current-version wording such as `Kimi Code 0.10.x`; classify any remaining matches as accurate historical or Gemini-specific content or update them.
- [x] 6.3 Run `openspec validate document-kimi-provider-priority --strict` and `openspec validate --specs --strict`.
- [x] 6.4 Run the repository docs/lint checks needed for Markdown-only changes, at minimum `pixi run lint` if the final edit set touches files covered by Ruff.
