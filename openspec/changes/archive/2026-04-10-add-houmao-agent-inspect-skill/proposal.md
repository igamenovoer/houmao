## Why

Inspection of Houmao-managed agents is currently split across lifecycle, messaging, gateway, mailbox, and filesystem-oriented surfaces. That makes it hard for operators and installed skills to answer a basic question such as "what is this agent doing right now, what backs it, and what can I safely inspect next?" without mixing read-only inspection with control or mutation workflows.

The repository now has enough supported inspection surfaces to support a dedicated skill: summary managed-agent state, detailed transport-specific state, gateway-owned TUI tracking, mailbox discovery and status, headless turn artifacts, runtime manifests, and session-owned gateway files. A dedicated `houmao-agent-inspect` skill should turn those fragmented surfaces into one read-oriented workflow with explicit boundaries.

## What Changes

- Add a packaged Houmao-owned system skill named `houmao-agent-inspect`.
- Define read-only inspection guidance for managed-agent discovery, liveness, transport-specific detail, mailbox posture, logs, runtime artifacts, and optional raw tmux peeking.
- Make the new skill prefer supported managed-agent and gateway inspection surfaces before local filesystem or tmux fallback.
- Add the new skill to the packaged system-skill catalog, named sets, and default installation selections.
- Clarify skill-family ownership so generic managed-agent inspection routes through `houmao-agent-inspect` instead of being implied by lifecycle or other operational skills.

## Capabilities

### New Capabilities
- `houmao-agent-inspect-skill`: Packaged read-only inspection guidance for Houmao-managed agents across discovery, TUI or headless state, mailbox posture, logs, runtime artifacts, and controlled tmux peeking.

### Modified Capabilities
- `houmao-agent-messaging-skill`: Clarify that generic managed-agent inspection belongs to `houmao-agent-inspect` even when messaging workflows still use discovery and gateway-owned TUI state for prompt-routing or queue-specific work.
- `houmao-agent-gateway-skill`: Clarify the boundary between gateway lifecycle or gateway-only control work and generic managed-agent inspection routed through `houmao-agent-inspect`.
- `houmao-mgr-system-skills-cli`: Surface `houmao-agent-inspect` and its named set in packaged skill inventory, install results, and status reporting.
- `houmao-system-skill-installation`: Add `houmao-agent-inspect` to the packaged catalog, define its named set, and include it in the fixed default install selections.

## Impact

- System skill assets under `src/houmao/agents/assets/system_skills/`
- Packaged system-skill catalog and install-selection logic under `src/houmao/agents/system_skills.py` and catalog assets
- Existing skill specs and packaging tests that enumerate installable Houmao-owned skills
- Operator and developer guidance that currently points generic inspection toward lifecycle, gateway, or mailbox surfaces without a dedicated inspection skill
