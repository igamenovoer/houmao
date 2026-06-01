## Why

Houmao system skills currently encode sparse-profile defaults and option semantics in Markdown, which lets skill guidance drift away from the CLI truth. This already surfaced in prompt-mode handling: an agent can accidentally persist `--prompt-mode unattended` when the desired behavior is to omit the field and let the default launch policy resolve it.

## What Changes

- Add a CLI-owned command-template renderer under `houmao-mgr internals` for agent-facing authoring workflows.
- Represent each supported authoring surface with an authoritative template that lists required fields, optional fields, omit-vs-set semantics, clear semantics, option mappings, conflicts, and conditional rules.
- Make the renderer accept sparse structured intent and return an exact `argv` array plus human-readable omitted/defaulted field explanations, warnings, and blockers without executing the command.
- Cover only templates that correspond to existing `houmao-mgr` command surfaces, including agent definitions, credentials, lifecycle launch/join/relaunch/cleanup, gateway controls, mailbox administration, managed-agent mail fallback commands, and profile-owned memo seed flags.
- Update packaged Houmao skills to start supported command authoring from the CLI template renderer instead of maintaining their own default templates in skill text.
- Leave skill-native loop scaffolds, workspace layouts, semantic workflow prompts, tours, and advanced examples in their skills unless a separate `houmao-mgr` command surface owns that behavior later.
- Preserve sparse defaults by omission, especially prompt mode and TUI/headless posture: omitted `prompt_mode` remains unset/inherited, and omitted launch posture remains TUI/local-interactive preferred where supported.

## Capabilities

### New Capabilities
- `houmao-mgr-command-template-renderer`: CLI-owned command templates and sparse intent rendering for agent-driven Houmao command authoring.

### Modified Capabilities
- `houmao-manage-agent-definition-skill`: Require the packaged agent-definition skill to use CLI-owned templates for supported specialist/profile/raw-profile/launch command authoring and to avoid owning semantic defaults in Markdown.
- `houmao-create-specialist-skill`: Require the specialist-management skill to use CLI-owned templates for supported specialist create/set and specialist-backed launch command authoring.
- `houmao-manage-credentials-skill`: Require the credential-management skill to use CLI-owned templates for supported credential command authoring and tool-specific credential option shapes.
- `houmao-manage-agent-instance-skill`: Require the agent-instance skill to use CLI-owned templates for supported launch, join, relaunch, and cleanup command authoring.
- `houmao-agent-gateway-skill`: Require the gateway skill to use CLI-owned templates for supported gateway control, notifier, and reminder command authoring.
- `houmao-mailbox-mgr-skill`: Require the mailbox-manager skill to use CLI-owned templates for supported mailbox, project mailbox, and managed-agent mailbox command authoring.
- `houmao-agent-email-comms-skill`: Require the email communications skill to use CLI-owned templates for supported `houmao-mgr agents mail ...` fallback commands while keeping HTTP/mail workflow prose in the skill.
- `houmao-memory-mgr-skill`: Clarify that memo seed command flags are owned through profile templates, while live memory workflows remain skill guidance.
- `houmao-mgr-project-easy-cli`: Clarify that easy specialist/profile create/set and instance launch are covered by the template registry and that omitted template fields preserve the underlying CLI defaults.
- `houmao-mgr-project-agents-roles`: Clarify that role init/set are covered by the template registry.
- `houmao-mgr-project-agents-presets`: Clarify that canonical recipe add/set are covered by the template registry.
- `houmao-mgr-project-agents-launch-profiles`: Clarify that recipe-backed launch-profile add/set are covered by the template registry and that omitted template fields preserve create-vs-patch semantics.
- `houmao-mgr-credentials-cli`: Clarify that credential command families are covered by the template registry for project and plain agent-definition lanes.
- `houmao-mgr-agents-launch`, `houmao-mgr-agents-join`, and `houmao-mgr-cleanup-cli`: Clarify lifecycle command-template coverage.
- `agent-gateway`: Clarify gateway control, notifier, and reminder command-template coverage.
- `houmao-mgr-mailbox-cli` and `houmao-mgr-project-mailbox-cli`: Clarify mailbox command-template coverage.

## Impact

- Affects `houmao-mgr internals` command routing and structured output.
- Adds a CLI-side command-template registry and renderer near the project/easy and project/agents command definitions.
- Updates packaged system-skill assets for agent definition, specialist management, credentials, agent instance lifecycle, gateway, mailbox, managed-agent email fallback, and memo seed profile authoring to call template `show`/`render` before issuing supported authoring commands.
- Adds unit coverage for template metadata, sparse rendering, conflict reporting, prompt-mode omission, headless/TUI omission, and system-skill guidance.
