## 1. Mailbox Skill Projection

- [ ] 1.1 Remove hidden mailbox compatibility-path constants, helpers, and projection writes so runtime-owned mailbox skills are projected only under `skills/mailbox/...`.
- [ ] 1.2 Update any runtime or demo-pack staging code that currently sources or copies mailbox skills through `skills/.system/mailbox/...` to use the visible mailbox tree or packaged source assets directly.

## 2. Prompt And Fixture Cleanup

- [ ] 2.1 Update runtime `mail` prompts and gateway notifier prompts to reference only `skills/mailbox/...` and stop mentioning hidden mailbox mirror paths.
- [ ] 2.2 Update repo-owned fixture prompts and demo-pack prompt text that still mention `skills/.system/mailbox/...` so they use the visible mailbox skill path only.

## 3. Docs And Regression Coverage

- [ ] 3.1 Update mailbox reference docs and any other repo-owned docs that describe `.system/mailbox/...` as a mailbox-skill location.
- [ ] 3.2 Update unit and integration tests that currently assert hidden mailbox skill projection or hidden-path prompt text, and add coverage that mailbox skills are projected only under `skills/mailbox/...`.
- [ ] 3.3 Verify the change with targeted mailbox projection, prompt, and demo-pack test coverage, and confirm `pixi run openspec status --change remove-mailbox-skill-compatibility-mirrors` is apply-ready.
