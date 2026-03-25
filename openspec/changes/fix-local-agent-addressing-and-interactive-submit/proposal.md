## Why

The serverless `houmao-mgr agents` workflow currently mixes a globally unique internal identity with a friendly user-facing name without making that split explicit. By contract, `agent_id` is the globally unique authoritative identity, while `agent_name` is only a friendly label and is not unique by design; local and pair-native CLI surfaces need to stop pretending one positional `<agent-ref>` can always safely mean both. Separately, local-interactive prompt submission can stage text in the provider TUI without producing a real submitted turn, which breaks both direct prompting and gateway-mediated prompting for Codex-backed local sessions.

## What Changes

- Define `agent_id` as the globally unique authoritative identity used for internal addressing, registry layout, and unambiguous CLI control, while `agent_name` becomes a non-unique friendly label that is only usable for control when the live registry has exactly one match.
- Require both `agent_id` and `agent_name` to use filepath-friendly and URL-friendly forms so they remain safe to place in paths, registry keys, and managed-agent HTTP routes.
- Keep user-owned identity input on launch: `agent_name` remains required, `agent_id` remains optional, and the effective default `agent_id` remains `md5(agent_name).hexdigest()` when the caller does not provide one.
- Reshape `houmao-mgr agents` command targeting to use explicit `--agent-id <id>` and `--agent-name <name>` selectors instead of one positional managed-agent reference, requiring callers to provide exactly one of those selectors when targeting a managed agent.
- Make `houmao-mgr agents launch` surface `agent_name`, effective `agent_id`, and tmux session name separately so operators can discover the right follow-up handle immediately.
- Split semantic prompt submission from raw key/control-input delivery across runtime and gateway boundaries, keeping `<[key-name]>` control sequences on a dedicated `send-keys` path and reserving `send-prompt` for literal text plus automatic submit.
- Change local-interactive prompt submission to use a submit-aware tmux delivery strategy so pasted prompt text and the submit action are not collapsed into one fast literal key stream that provider TUIs can reinterpret as multiline draft input.
- Update gateway-mediated prompt semantics, docs, and workflow coverage so successful prompt submission means the underlying TUI actually receives a submitted turn rather than only a staged draft.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-discovery-registry`: registry identity rules treat `agent_id` as globally unique, `agent_name` as non-unique friendly metadata, and require both fields to remain filepath-friendly and URL-friendly.
- `houmao-srv-ctrl-native-cli`: managed-agent subcommands move to explicit `--agent-id` / `--agent-name` selectors instead of a single positional managed-agent reference.
- `houmao-mgr-registry-discovery`: local registry-first discovery resolves by exact `agent_id`, by unique `agent_name`, or by unique tmux session alias, and fails clearly when friendly names are ambiguous.
- `houmao-mgr-agents-launch`: launch output distinguishes `agent_name`, effective `agent_id`, and tmux session handles so operators can immediately discover all addressing forms.
- `brain-launch-runtime`: local-interactive prompt submission becomes a semantic submit operation distinct from raw key injection and must produce a real submitted provider turn.
- `agent-gateway`: gateway prompt submission for local tmux-backed agents uses the semantic prompt path, while raw `<[key-name]>` control input remains a separate explicit operation.

## Impact

Affected areas include shared-registry identity validation and lookup, `src/houmao/srv_ctrl/commands/agents/core.py`, `src/houmao/srv_ctrl/commands/managed_agents.py`, native CLI option parsing for managed-agent subcommands, local-interactive tmux delivery helpers, and gateway request/adapter handling. Docs and workflow tests for local launch, agent targeting, gateway attach, and TUI-state tracking will need updates to reflect the new addressing guidance and the split between prompt submission and raw key delivery.
