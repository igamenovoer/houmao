## 1. Command Shape

- [x] 1.1 Add `houmao-mgr agents global`, `houmao-mgr agents single`, `houmao-mgr agents self`, and `houmao-mgr agents external` command groups under the existing `agents` namespace.
- [x] 1.2 Move zero-or-many local managed-agent registry/fleet operations from root `agents` to `agents global`, starting with `list`.
- [x] 1.3 Move one-agent lifecycle commands from root `agents` to `agents single`, including `state`, `prompt`, `interrupt`, `stop`, and `relaunch`.
- [x] 1.4 Move one-agent subfamilies from root `agents` to `agents single`, including `gateway`, `mail`, `mailbox`, `memory`, `turn`, and `cleanup`.
- [x] 1.5 Move current-session adoption from root `agents join` to `agents self join`.
- [x] 1.6 Move external-agent registry/reference onboarding commands from root `agents external` to the direct `agents external` family, without adding external lifecycle control.
- [x] 1.7 Remove direct root-level `agents` action commands so `houmao-mgr agents --help` exposes only scoped `global`, `single`, `self`, and `external` groups.
- [x] 1.8 Add `agents self` command wrappers for current-session operations, including `identity`, `state`, `prompt`, `interrupt`, narrow active-surface `relaunch`, `gateway`, `mail`, `mailbox`, `memory`, and `turn`.
- [x] 1.9 Do not register destructive selected-agent lifecycle controls under `agents self`; `agents self stop` and `agents self cleanup` must not be maintained public paths.

## 2. Target Resolution

- [x] 2.1 Add a typed group-level target context for `agents single`.
- [x] 2.2 Make `agents single` require exactly one of `--agent-id <id>` or `--agent-name <name>`.
- [x] 2.3 Update nested `agents single` command handlers to consume the group-level selector instead of leaf-level `--agent-id` and `--agent-name` options.
- [x] 2.4 Make `agents single` reject omitted selectors instead of falling back to current tmux session metadata.
- [x] 2.5 Make `agents self join` adopt the current tmux session into the Houmao managed-agent registry.
- [x] 2.6 Make `agents self` follow-up commands resolve the target from the current managed tmux session and fail clearly outside a registered managed session.
- [x] 2.7 Ensure `agents self` follow-up commands do not expose or accept `--agent-id`, `--agent-name`, or `--current-session`.
- [x] 2.8 Preserve pair-authority and tmux-session targeting behavior only where it still fits the selected single-agent or self command contract.
- [x] 2.9 Gate command availability by authority surface so destructive or session-invalidating lifecycle controls require explicit `agents single --agent-id <id>` or `agents single --agent-name <name>` targeting.
- [x] 2.10 Implement `agents self relaunch` as active-current-session refresh only: require current-session manifest authority and do not perform selected-agent registry lookup, stopped relaunchable-record revival, degraded/stale active-record recovery, or cross-session targeting.
- [x] 2.11 Ensure `agents global` commands do not accept single-agent selectors and only represent no-agent registry queries or multi-agent fleet operations.

## 3. Launch And Project Boundaries

- [x] 3.1 Remove maintained public root/global/single managed-agent launch paths from the `agents` command family.
- [x] 3.2 Route project launch-profile usage to `houmao-mgr project [--project-dir <dir>] agents launch --profile <name>`.
- [x] 3.3 Keep `project agents launch --specialist` and `project agents launch --profile` project-scoped through the selected project overlay.
- [x] 3.4 Keep `project agents list|get|stop` ownership checks so cross-project registry records are rejected.
- [x] 3.5 Add or preserve project-agent follow-up operations only when they validate selected-project ownership before acting.

## 4. Command Templates And Skills

- [x] 4.1 Update command-template ids and rendered argv for zero-or-many managed-agent commands to use `agents global ...`.
- [x] 4.2 Update selected one-agent command templates to render `agents single --agent-id <id> ...` or `agents single --agent-name <name> ...`.
- [x] 4.3 Add or update current-session command templates to render `agents self ...` without explicit target selectors, including `agents self join` for current-session adoption and `agents self relaunch` for active-current-session refresh.
- [x] 4.4 Update external-reference templates to render `agents external ...` while avoiding lifecycle-control templates for external runtimes.
- [x] 4.5 Update project-agent templates to render `project [--project-dir <dir>] agents ...`.
- [x] 4.6 Sweep packaged system-skill guidance for old `houmao-mgr agents ...` paths and replace them with `agents global`, `agents single`, `agents self`, `agents external`, or `project agents` according to target ownership.
- [x] 4.7 Keep command-template list/show/render output free of ambiguous root-level `agents <verb>` paths, public global/single launch templates, destructive self lifecycle templates such as `agents self stop`, and external lifecycle templates.

## 5. Documentation

- [x] 5.1 Update `docs/reference/cli/houmao-mgr.md` and nested CLI pages to present `agents global`, `agents single`, `agents self`, and `agents external`.
- [x] 5.2 Add migration examples from old ambiguous `agents ...` paths to scoped `agents global`, `agents single`, `agents self`, `agents external`, and `project agents` paths.
- [x] 5.3 Update docs for `agents single mail`, `agents self mail`, `agents single gateway`, `agents self gateway`, and `agents external` selector/authority semantics.
- [x] 5.4 Document the target cardinality split: `agents global` is zero-or-many, `agents single` is exactly one explicit selected agent, `agents self` is exactly one current-session agent, and `agents external` is registry/reference onboarding without local lifecycle authority.
- [x] 5.5 Document that `agents single` and `agents self` are separate authority surfaces, not aliases; `self relaunch` is active-current-session refresh only, while selected-agent stopped/degraded relaunch recovery remains under `single`.
- [x] 5.6 Update project-aware docs so `project agents` is described as selected-project agent-instance management rather than global registry control.
- [x] 5.7 Remove stale examples that use direct root-level `houmao-mgr agents launch`, `agents mail`, `agents gateway`, or `agents turn` as maintained public paths.
- [x] 5.8 Remove stale examples that present `agents global launch`, `agents single launch`, `agents global external`, `agents self stop`, or `agents self cleanup` as maintained public paths.

## 6. Tests And Verification

- [x] 6.1 Add CLI help tests proving `agents` exposes `global`, `single`, `self`, and `external` and no longer exposes direct root-level action commands.
- [x] 6.2 Add routing tests for representative `agents global list`.
- [x] 6.3 Add routing tests for representative `agents single` lifecycle, gateway, mail, mailbox, memory, turn, and cleanup commands.
- [x] 6.4 Add routing tests for `agents external register|list|get|verify|remove`.
- [x] 6.5 Add self-join tests proving `agents self join` adopts the current tmux session.
- [x] 6.6 Add self-target tests proving `agents self` follow-up commands resolve current tmux identity and reject explicit selectors.
- [x] 6.7 Add self-routing tests proving `agents self prompt`, `agents self interrupt`, and `agents self relaunch` are maintained current-session paths.
- [x] 6.8 Add self-relaunch tests proving `agents self relaunch` uses current-session manifest authority and does not perform stopped/degraded selected-agent recovery.
- [x] 6.9 Add self-help/routing tests proving `agents self stop` and `agents self cleanup` are not maintained public paths.
- [x] 6.10 Add single-target tests proving `agents single` rejects omitted selectors even inside tmux and propagates group-level selectors to nested commands.
- [x] 6.11 Add global-target tests proving `agents global` does not accept `--agent-id` or `--agent-name`.
- [x] 6.12 Add external-authority tests proving `agents external` does not expose local lifecycle controls.
- [x] 6.13 Add launch tests proving root/global/single `agents launch`, `agents global launch`, and `agents single launch` are not maintained public paths.
- [x] 6.14 Add project-agent ownership tests for selected overlay list/get/stop and project profile launch.
- [x] 6.15 Add command-template tests for `agents global`, `agents single`, `agents self`, `agents external`, and `project [--project-dir] agents` rendering, including `agents self relaunch` plus the absence of destructive self lifecycle templates and external lifecycle templates.
- [x] 6.16 Run `pixi run format`, `pixi run lint`, `pixi run typecheck`, `pixi run test`, and `openspec validate split-agents-global-self-cli --strict`.
