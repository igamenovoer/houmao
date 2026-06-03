## Why

`houmao-mgr agents` currently mixes distinct modes: zero-or-many operations over the shared managed-agent registry, explicit operations against one selected managed agent, current-agent operations inferred from the caller's tmux session, and external-agent reference onboarding. That context-sensitive behavior overlaps with `houmao-mgr project agents`, makes command intent harder to read, and keeps reintroducing top-level commands whose target is selected implicitly.

The selected-agent and current-session modes also have different authority boundaries. Some commands are only sensible for the current tmux session, such as joining the registry as self. Some commands are shared but have narrower self semantics, such as `relaunch`: selected-agent relaunch may revive stopped or degraded registry records, while self relaunch only refreshes the active tmux-backed surface for the caller's current managed session. Other commands, such as stopping or cleaning up a tmux-backed managed agent, should only be invoked through an explicit selected-agent target from outside that session. This change preserves separate `single` and `self` groups so the CLI shape can encode those differences directly.

## What Changes

- **BREAKING**: Split the public `houmao-mgr agents` family into explicit `global`, `single`, `self`, and `external` subgroups.
- **BREAKING**: Move zero-or-many local managed-agent shared-registry operations to `houmao-mgr agents global ...`.
- **BREAKING**: Move explicitly selected one-agent operations to `houmao-mgr agents single --agent-id <id> ...` or `houmao-mgr agents single --agent-name <name> ...`.
- **BREAKING**: Move current-tmux-session operations for the agent that owns the caller's session to `houmao-mgr agents self ...`.
- **BREAKING**: Move current-session adoption to `houmao-mgr agents self join ...`.
- **BREAKING**: Keep `agents single` and `agents self` as distinct operation families rather than selector aliases: `prompt`, `interrupt`, and `relaunch` may exist in both, but `self relaunch` is active-current-session refresh only; selected-agent `stop`, selected-agent stopped/degraded relaunch recovery, and `cleanup` belong to `single`.
- **BREAKING**: Move external-agent registry/reference onboarding to `houmao-mgr agents external ...`; external agents may be visible in Houmao's managed registry, but their lifecycle is not controlled by this user's `houmao-mgr`.
- **BREAKING**: Remove implicit current-session targeting from non-self commands; selected one-agent operations use the `agents single` group-level selector.
- **BREAKING**: Remove managed-agent birth from the global management surface; project-backed launch remains under `houmao-mgr project [--project-dir <dir>] agents launch`, while direct native/provider plumbing remains internal.
- Keep `houmao-mgr project agents ...` as the selected-project facade for project-owned agent instances, using project-local names and rejecting cross-project targets.
- Update command-template coverage, packaged skill guidance, and CLI docs so examples use `project agents`, `agents global`, `agents single`, `agents self`, or `agents external` according to target ownership.

## Capabilities

### New Capabilities

- `houmao-mgr-agents-scope-cli`: Defines the explicit `agents global`, `agents single`, `agents self`, and `agents external` command-scope split, target cardinality rules, current-session join semantics, selected-agent lifecycle authority, external-agent lifecycle limits, and migration away from implicit current-session targeting.

### Modified Capabilities

- `houmao-mgr-agents-launch`: Retire the public root/global launch surface and keep managed-agent birth source-scoped through project or internal native-agent surfaces.
- `houmao-mgr-project-cli`: Clarify that `project agents` is the selected-project agent-instance facade and may expose project-owned lifecycle/follow-up operations without crossing overlay boundaries.
- `houmao-mgr-command-template-renderer`: Update command-template families to render `agents global ...`, `agents single ...`, `agents self ...`, `agents external ...`, and `project [--project-dir] agents ...` paths rather than ambiguous `agents ...` paths.
- `docs-cli-reference`: Update CLI reference coverage and examples for the new `agents global` / `agents single` / `agents self` / `agents external` split and the narrowed `project agents` responsibility.

## Impact

- CLI command modules under `src/houmao/srv_ctrl/commands/agents/` and their registration in the top-level `agents` group.
- Project agent commands in `src/houmao/srv_ctrl/commands/project_easy.py` and shared project ownership checks.
- Current-session target resolution helpers used by join, gateway, mail, mailbox, memory, and turn commands.
- Command template registration/rendering under `src/houmao/srv_ctrl/command_templates/`.
- Docs under `docs/reference/cli/`, project-aware docs, and packaged system-skill guidance that references managed-agent command paths.
- Unit tests for CLI help, command routing, current-session fallback, project ownership checks, and command templates.
