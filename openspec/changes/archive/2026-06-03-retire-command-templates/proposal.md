## Why

`houmao-mgr internals command-templates` is a historical mis-implementation: it turned ordinary executable command spelling into a second templating system that agents must consult before running maintained CLI commands. Houmao now has the clearer split we want: `config-drafts` owns YAML authoring templates, while executable workflows should be documented directly as shell commands in packaged skills.

## What Changes

- **BREAKING** Remove the `houmao-mgr internals command-templates` subcommand family, including `list`, `show`, `render`, and `export`.
- **BREAKING** Remove the Python command-template registry, renderer, exporter, family modules, and command-template compatibility imports.
- Replace packaged skill guidance that calls `internals command-templates show|render` with direct fenced `bash` command examples for executable `houmao-mgr` commands.
- Keep `houmao-mgr internals config-drafts` as the only CLI-owned template-like surface, scoped to generating YAML/config documents and not executable argv.
- Update specs and tests so maintained CLI surfaces are validated directly, not through command-template entries.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `houmao-mgr-command-template-renderer`: retire and remove the command-template renderer capability.
- `houmao-mgr-config-drafts`: clarify that config drafts are the maintained YAML template surface and do not imply executable command rendering.
- `houmao-manage-agent-definition-skill`: replace command-template guidance with config-drafts for YAML and direct command snippets for executable flows.
- `houmao-manage-agent-instance-skill`: replace command-template guidance with direct lifecycle command snippets.
- `houmao-manage-credentials-skill`: replace command-template guidance with direct credential command snippets.
- `houmao-agent-gateway-skill`: replace command-template guidance with direct gateway command snippets.
- `houmao-agent-email-comms-skill`: replace command-template guidance with direct mail fallback command snippets.
- `houmao-mailbox-mgr-skill`: replace command-template guidance with direct mailbox command snippets.
- `houmao-create-specialist-skill`: remove command-template blocker handling from specialist workflow requirements.
- `houmao-memory-mgr-skill`: remove future command-template language from memory command guidance.
- `houmao-mgr-project-easy-cli`: remove requirements for project command-template entries.
- `houmao-mgr-agents-launch`: remove requirements for relaunch command-template entries.
- `houmao-mgr-agents-join`: remove requirements for join command-template entries.
- `houmao-mgr-cleanup-cli`: remove requirements for cleanup command-template entries.
- `houmao-mgr-credentials-cli`: remove requirements for credential command-template entries.
- `houmao-mgr-mailbox-cli`: remove requirements for shared mailbox command-template entries.
- `houmao-mgr-project-mailbox-cli`: remove requirements for project mailbox command-template entries.
- `agent-gateway`: remove requirements for gateway command-template entries.

## Impact

- Affected CLI code: `src/houmao/srv_ctrl/commands/internals.py`, `src/houmao/srv_ctrl/commands/command_templates.py`, and `src/houmao/srv_ctrl/command_templates/`.
- Affected tests: command-template unit tests are removed or replaced by direct CLI and skill-content assertions.
- Affected packaged skills: agent definition, instance, credentials, gateway, mailbox, and email-comms skills stop consulting command templates.
- Affected specs: existing command-template requirements are removed or rewritten around direct command guidance and config-draft usage.
