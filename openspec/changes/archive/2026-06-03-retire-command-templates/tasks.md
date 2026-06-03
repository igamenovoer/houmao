## 1. Remove Command-Template Runtime Surface

- [x] 1.1 Remove `houmao-mgr internals command-templates` registration and command handlers from the internals CLI.
- [x] 1.2 Delete the command-template registry, renderer, exporter, datamodel, family modules, and compatibility re-export module.
- [x] 1.3 Remove imports and package exports that expose `houmao.srv_ctrl.command_templates`.
- [x] 1.4 Add or update CLI assertions showing `command-templates` is no longer listed under `houmao-mgr internals`.

## 2. Rewrite Packaged Skill Guidance

- [x] 2.1 Update `houmao-agent-definition` to use `config-drafts` only for YAML documents and direct fenced `bash` snippets for roles, recipes, brain build, and launch commands.
- [x] 2.2 Update `houmao-agent-instance` launch, join, relaunch, and cleanup guidance to show direct scoped `houmao-mgr` commands.
- [x] 2.3 Update `houmao-credential-mgr` guidance and action files to show direct project and native-agent credential commands for Claude, Codex, and Gemini lanes.
- [x] 2.4 Update `houmao-agent-gateway` guidance and action files to show direct scoped gateway, notifier, TUI, and reminder commands.
- [x] 2.5 Update `houmao-mailbox-mgr` and `houmao-agent-email-comms` guidance to show direct mailbox and managed-agent mail fallback commands.
- [x] 2.6 Update `houmao-specialist-mgr` compatibility guidance to delegate to config-draft and direct-command workflows instead of command-template rendering.
- [x] 2.7 Update any remaining packaged skill text that references command-template ids, template blockers, or `internals command-templates`.

## 3. Update Tests And Spec Coverage

- [x] 3.1 Remove command-template renderer/exporter unit tests that only validate the retired registry.
- [x] 3.2 Add focused content tests asserting packaged skills no longer reference `internals command-templates`, command-template ids, or command-template blockers.
- [x] 3.3 Update config-drafts tests that mention command-template metadata so they assert YAML-only/executable-command separation without the retired terminology.
- [x] 3.4 Update any CLI, docs, or fixture tests that expected command-template inventory entries.

## 4. Validate

- [x] 4.1 Run `openspec validate retire-command-templates --strict`.
- [x] 4.2 Run focused unit tests for internals CLI, config drafts, and packaged skill content.
- [x] 4.3 Run `pixi run lint`.
- [x] 4.4 Run `pixi run typecheck`.
- [x] 4.5 Run `pixi run test`.
