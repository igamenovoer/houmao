## Context

The native `houmao-mgr agents` tree currently exposes both `state` and `show` inspection commands. `state` provides the operational managed-agent summary view, while `show` adds a second detail-oriented CLI surface on top of the same managed-agent discovery path.

For current operator workflows, the extra `show` command is redundant with other supported inspection paths:

- `agents state` for the transport-neutral summary view,
- `agents gateway tui ...` for raw gateway-owned TUI inspection, and
- transport-specific or API-level detail routes where a richer detail payload is still needed outside the native CLI.

The repository is already willing to take breaking CLI simplifications, and this change is intentionally limited to the native `houmao-mgr agents show` subcommand rather than to the underlying managed-agent detail API.

## Goals / Non-Goals

**Goals:**
- Remove `houmao-mgr agents show` from the supported native CLI.
- Update the active OpenSpec capability specs that still reference `agents show` so the spec corpus describes one coherent native inspection surface and CLI documentation contract.
- Align help text, reference docs, workflows, and tests with the smaller inspection surface.
- Keep the rest of the `agents` command family stable, especially `state`, `prompt`, `interrupt`, `relaunch`, and gateway-specific inspection commands.

**Non-Goals:**
- Removing the managed-agent detail HTTP route or internal detail payload builders.
- Migrating demo or helper consumers that still call the preserved detail payload builder chain directly.
- Changing `houmao-mgr agents state` semantics.
- Refactoring gateway, passive-server, or server-managed inspection APIs beyond references to the removed CLI command.

## Decisions

### Remove only the native CLI subcommand
The change removes the `agents show` command registration, its CLI import/wiring, and related help/docs references, but does not remove the underlying managed-agent detail route or transport-specific detail models.

This keeps the change narrowly scoped to the user-facing CLI surface the user wants gone, avoids unnecessary churn in pair APIs, and leaves room for non-CLI consumers to keep using detail payloads where they still add value.

Alternative considered: keep `show` as a deprecated alias for one release. Rejected because the repository explicitly allows breaking changes and the requested outcome is to remove the subcommand rather than stretch out a compatibility window.

### Preserve the detail helper chain for non-CLI callers
The change keeps `managed_agent_detail_payload()` and its local detail helper chain in place for non-CLI callers even though the native `agents show` command goes away.

That choice avoids widening this change into direct-helper demo migration, pair-client refactors, or unrelated unit-test churn. The implementation work is therefore limited to removing the CLI entrypoint and any now-unused CLI import/wiring in `src/houmao/srv_ctrl/commands/agents/core.py`, while leaving the detail payload builder as a still-supported programmatic helper.

Alternative considered: remove the helper chain as CLI dead code. Rejected because the current change request is to remove the native CLI command, not to retire every non-CLI detail consumer in the repository.

### Migrate CLI-based demo consumers that still shell out to `agents show`
The preserved helper-chain decision does not exempt code that still invokes the removed CLI subcommand. Demo-pack runtime code that shells out to `houmao-mgr agents show` remains in scope for migration because it would fail immediately once the subcommand is removed.

That means this change still needs to update CLI consumers such as `src/houmao/demo/gateway_mail_wakeup_demo_pack/` even though direct helper consumers like `managed_agent_detail_payload()` remain supported.

### Keep `state` as the sole transport-neutral inspection command
After this change, the native `agents` tree will have one supported transport-neutral inspection command: `state`.

Operators who need richer live tracking or raw terminal-oriented inspection should use the already-supported gateway TUI commands instead of a second transport-neutral detail command.

Alternative considered: redirect `show` to `state`. Rejected because it preserves the extra command name and keeps the documentation and test matrix larger than necessary.

### Treat docs and workflow references as part of the removal
Removing the command cleanly requires updating command tables, help expectations, workflow docs, demo workflows, and active OpenSpec capability specs that currently instruct operators to run `agents show`.

Alternative considered: remove only the Python command and leave doc cleanup for later. Rejected because dangling references would make the breaking change look like a regression rather than an intentional CLI simplification.

## Risks / Trade-offs

- [Breaking scripts or operator muscle memory] → Update help text and docs to point to `agents state`, `agents gateway tui ...`, and other supported inspection paths; make the change explicit in the proposal and tasks.
- [Leaving hidden references behind] → Update the affected capability specs and use a repository-wide grep sweep for `agents show`, CLI help expectations, demo consumers, and workflow examples as part of implementation.
- [Future callers still wanting detail-rich CLI inspection] → Preserve the underlying managed-agent detail route and internal detail payload code so a future CLI surface could be reintroduced deliberately if needed.

## Migration Plan

- Remove the CLI subcommand implementation and its help exposure.
- Update the affected delta specs so `houmao-srv-ctrl-native-cli`, `houmao-mgr-agents-join`, `houmao-mgr-registry-discovery`, and `docs-cli-reference` stop requiring `agents show`.
- Update docs and workflow artifacts that advertise `agents show`.
- Migrate demo-pack runtime code that still shells out to `houmao-mgr agents show` onto a supported inspection path.
- Update CLI shape tests and any related fixtures to stop expecting the removed subcommand.
- Preserve server and passive-server detail APIs so non-CLI callers remain unaffected.

## Open Questions

- None for this scoped change. The only intentional decision is to remove the native CLI subcommand while preserving the underlying detail API.
