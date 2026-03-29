## 1. Project Init Defaults

- [x] 1.1 Update project-overlay bootstrap and `houmao-mgr project init` so `.houmao/agents/compatibility-profiles/` is not created by default.
- [x] 1.2 Add an explicit `project init` opt-in flag for compatibility-profile bootstrap and cover both default and opt-in behavior in project command tests.

## 2. Specialist Authoring Defaults

- [x] 2.1 Make `project easy specialist create --credential` optional, derive `<specialist-name>-creds` when omitted, and preserve the resolved credential name in command output and specialist metadata.
- [x] 2.2 Implement reuse/create/fail behavior for the resolved specialist auth bundle depending on whether auth inputs are provided and whether the target bundle already exists.
- [x] 2.3 Allow `project easy specialist create` to omit system prompt inputs while still materializing the canonical role prompt path as an intentionally empty file.

## 3. Runtime Empty-Prompt Handling

- [x] 3.1 Relax canonical role loading so an existing empty `roles/<role>/system-prompt.md` is treated as a valid no-system-prompt role package.
- [x] 3.2 Update native local/headless/app-server launch paths so empty role prompts do not emit empty developer-instructions, appended-system-prompt, or bootstrap-message startup inputs.
- [x] 3.3 Add or update runtime tests covering empty-prompt role loading and prompt-injection suppression for the affected backends.

## 4. Docs And Verification

- [x] 4.1 Update getting-started and CLI reference docs to reflect the new `project init` default, the compatibility-profile opt-in flag, optional specialist credentials, derived credential naming, and optional system prompts.
- [x] 4.2 Run targeted OpenSpec-aware verification plus relevant unit tests for project commands and runtime launch behavior, then confirm the change remains apply-ready.
