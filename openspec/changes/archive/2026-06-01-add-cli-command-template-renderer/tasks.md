## 1. Template Registry And Internals CLI

- [x] 1.1 Add a CLI-owned command-template data model for template id, target command path, required fields, optional fields, option mappings, omit semantics, clear semantics, conflicts, and conditional rules.
- [x] 1.2 Add initial template registry entries for easy specialist create/set, easy profile create/set, easy instance launch, low-level roles init/set, recipes add/set, and raw launch-profile add/set.
- [x] 1.3 Add `houmao-mgr internals command-templates list`, `show`, and `render` command wiring with shared structured output support.
- [x] 1.4 Make unknown template ids and unsupported render fields fail clearly with structured errors.
- [x] 1.5 Add registry grouping or metadata that marks every template as tied to an existing `houmao-mgr` command surface, and excludes skill-native scaffolds/prompts from command-template listing.

## 2. Renderer Behavior

- [x] 2.1 Implement sparse JSON intent rendering to exact argv and a shell-safe command string without executing the target command.
- [x] 2.2 Report normalized intent, applied fields, omitted fields, warnings, and blockers in render output.
- [x] 2.3 Preserve omitted prompt mode and omitted TUI/headless posture without injecting `--prompt-mode`, `--headless`, or clear flags.
- [x] 2.4 Implement clear-field rendering only for templates and surfaces that declare matching clear options.
- [x] 2.5 Implement conflict detection for mutually exclusive fields such as managed-header posture and launch posture.

## 3. Template Coverage

- [x] 3.1 Cover `project.easy.specialist.create` and `project.easy.specialist.set`, including credential, skill, prompt, prompt-mode, model, reasoning, and persistent env fields.
- [x] 3.2 Cover `project.easy.profile.create` and `project.easy.profile.set`, including specialist source, auth, workdir, mailbox, prompt overlay, managed-header, prompt-mode, model, reasoning, notifier appendix, and memo seed fields.
- [x] 3.3 Cover `project.easy.instance.launch`, including specialist/profile source selection, instance name, workdir, one-shot prompt/model/reasoning/posture overrides, mailbox launch flags, and managed-header section overrides.
- [x] 3.4 Cover `project.agents.roles.init`, `project.agents.roles.set`, `project.agents.recipes.add`, and `project.agents.recipes.set`, including prompt source conflicts, auth/skill clear fields, and prompt-mode omission.
- [x] 3.5 Cover `project.agents.launch-profiles.add` and `project.agents.launch-profiles.set`, including create-vs-patch omit semantics, raw-profile clear flags, mailbox/prompt-overlay/managed-header fields, and memo seed fields.
- [x] 3.6 Cover credential templates for Claude, Codex, and Gemini in project and plain agent-definition lanes, including add/set/login/list/get/rename/remove verbs and tool-specific credential source conflicts.
- [x] 3.7 Cover agent lifecycle templates for direct launch, launch-profile launch, join, relaunch, cleanup session, and cleanup logs.
- [x] 3.8 Cover gateway templates for status/attach/detach/prompt/interrupt/send-keys/TUI helpers, mail-notifier status/enable/disable, and reminders list/get/create/set/remove.
- [x] 3.9 Cover mailbox templates for shared mailbox, project mailbox, project mailbox account/message commands, and managed-agent mailbox register/status/unregister.
- [x] 3.10 Cover managed-agent mail fallback templates for `agents mail resolve-live|status|list|peek|read|send|post|reply|mark|move|archive`.

## 4. System Skill Updates

- [x] 4.1 Update `houmao-agent-definition` guidance so supported specialist, profile, role, recipe, raw-profile, fast-forward, and launch authoring flows start from `internals command-templates show|render`.
- [x] 4.2 Update `houmao-specialist-mgr` guidance so it delegates specialist create/set and specialist-backed launch flows to the same CLI-owned templates rather than owning a separate command catalog.
- [x] 4.3 Update `houmao-credential-mgr` guidance so supported credential command authoring and Claude/Codex/Gemini option shapes come from credential templates.
- [x] 4.4 Update `houmao-agent-instance` guidance so supported launch, join, relaunch, and cleanup commands start from lifecycle templates.
- [x] 4.5 Update `houmao-agent-gateway` guidance so supported gateway command authoring starts from gateway templates while HTTP workflow guidance stays skill-owned.
- [x] 4.6 Update `houmao-mailbox-mgr` guidance so supported mailbox command authoring starts from mailbox templates while transport explanations stay skill-owned.
- [x] 4.7 Update `houmao-agent-email-comms` guidance so supported `agents mail ...` fallback command authoring starts from mail fallback templates while HTTP-vs-CLI routing stays skill-owned.
- [x] 4.8 Update `houmao-memory-mgr` guidance so profile-owned memo seed fields point to profile templates while live memory workflows remain direct skill guidance.
- [x] 4.9 Remove or shorten skill-owned default-bearing command skeletons for covered command surfaces.
- [x] 4.10 Keep workflow scaffolds, semantic prompts, tours, advanced examples, and unsupported command guidance in their owning skills.

## 5. Verification

- [x] 5.1 Add unit tests for template list/show output and required metadata for every initial template id or template family.
- [x] 5.2 Add renderer tests for sparse prompt-mode omission, TUI/headless omission, explicit prompt-mode set, explicit clear prompt mode, raw-profile patch preservation, lifecycle posture omission, credential source conflicts, gateway reminder conflicts, mailbox selector conflicts, and managed-agent mail fallback rendering.
- [x] 5.3 Add tests or golden checks for updated packaged skill guidance so it references the CLI-owned templates and does not reintroduce default-bearing skeletons for covered command surfaces.
- [x] 5.4 Add tests that command-template listing excludes loop/workspace scaffolds and semantic workflow prompt templates.
- [x] 5.5 Run focused unit tests for command-template behavior and packaged skill assets.
- [x] 5.6 Run `pixi run lint` and the relevant broader test command before closing the change.
