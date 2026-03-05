## Why

Claude-backed sessions run with `CLAUDE_CONFIG_DIR` set to an isolated, fresh runtime “brain home”. Claude Code v2.x treats an empty config directory as first-run and can enter interactive onboarding / approval flows (and may contact `api.anthropic.com` regardless of `ANTHROPIC_BASE_URL`). In CAO-backed tmux sessions this can block startup and cause timeouts, making the Claude demo and runtime unreliable in restricted network environments.

## What Changes

- Define an explicit contract for preparing a Claude brain home so Claude Code can start non-interactively in an isolated `CLAUDE_CONFIG_DIR`, including a credential-profile template `agents/brains/api-creds/claude/<cred-profile>/files/claude_state.template.json` projected into the runtime home and used to materialize `$CLAUDE_CONFIG_DIR/.claude.json`.
- Define launch invariants for orchestrated Claude Code runs (environment + flags) so startup does not block on first-run prompts, including headless launch args being tool-adapter-configurable and CAO/tmux session environment inheriting the calling process environment plus credential-profile env overlay.
- Clarify the “fresh-by-default runtime home” requirement to allow minimal, deterministic tool bootstrap config/state needed for non-interactive startup (without copying prior-run history/log/session artifacts).

## Capabilities

### New Capabilities

- `claude-cli-noninteractive-startup`: Specify the minimum Claude brain-home config/state and launch invariants required for unattended startup in `CLAUDE_CONFIG_DIR`.

### Modified Capabilities

- `component-agent-construction`: Refine the definition of “fresh runtime home” to explicitly permit tool bootstrap config/state (while still forbidding copied-in prior-run history/log/session artifacts).

## Impact

- Affected areas: brain construction (`agents/brains/...`), Claude credential profiles (`agents/brains/api-creds/claude/...`), brain launch runtime backends (especially tmux/CAO-backed launch), and documentation/tests that assert “fresh home” semantics.
- External dependencies: none (contract-level change; implementation should remain within the existing Python + shell tooling).
