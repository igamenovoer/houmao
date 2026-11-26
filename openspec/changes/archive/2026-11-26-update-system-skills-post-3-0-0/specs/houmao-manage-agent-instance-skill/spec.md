# Spec Delta

## ADDED Requirements

### Requirement: Agent instance manager covers external agents, executor bindings, launch flags, and relaunch behavior
`houmao-manage-agent-instance-skill` (`houmao-agent-instance`) SHALL cover `agents external {register|list|get|verify|remove}`, `--executor` and `admin executors reconcile|forget` boundaries, `open-browser` cross-link, `--headless-display-*`, `--tool-params`, `--reuse-home`, `--force`, `--agent-id-mode`, `--gateway-admin-seed`, and `relaunch` preservation of `--tmux-server` and mode plus DSH ACP `gateway detach`/`attach`.

#### Scenario: Operator launches, relaunches, or registers an external agent
- **WHEN** an admin launches with `--executor` / `--headless-display-*` / `--reuse-home` / `--force`, relaunches a DSH ACP session, or registers a remote peer via `agents external`
- **THEN** `commands/launch.md`, `commands/relaunch.md`, and `SKILL-MAIN.md` document exact flags, DSH ACP gateway re-attach requirements, and `agents external` local-only import semantics

### Requirement: Agent instance manager fixes duplicate guardrail and streamlines SKILL-MAIN.md and launch.md
`houmao-agent-instance` SHALL remove the duplicate `--purge-registry` guardrail in `commands/cleanup.md` (lines 38 and 40), replace repeated option lists in `commands/launch.md` with a clean options table (including `--tmux-server` on specialist-backed launches), and strip launcher, Missing-Input, `houmao-cli`, and Scope/Routing boilerplate in `SKILL-MAIN.md` (~95 lines).

#### Scenario: Cleanup guardrails and launch tables contain no duplication
- **WHEN** a reviewer inspects `houmao-agent-instance`
- **THEN** `commands/cleanup.md` contains no duplicate guardrail line, `commands/launch.md` presents launch options in a concise table, and `SKILL-MAIN.md` removes cross-skill boilerplate

### Requirement: Agent instance manager preserves actor scopes, state subsurfaces, and tmux server isolation
`houmao-agent-instance` SHALL preserve `## Actor Frame Gate`, admin vs `agents self` lifecycle scopes, `native-resources` (`home`, `refresh` never installing or editing gateway mounts), `runtime-variables` (CAS `--expected-revision`, no secrets), `mindsets` (fail-closed `snapshot`), `private-workspace` separation from `utils-workspace-mgr`, and `--tmux-server` isolation.

#### Scenario: Native refresh, runtime variables, and private workspace keep strict boundaries
- **WHEN** an agent or admin uses `native-resources`, `runtime-variables`, `mindsets`, or `private-workspace`
- **THEN** `refresh` does not mutate gateway mounts, `runtime-variables` stores no secrets, `mindsets` fails closed on snapshot failure, and `private-workspace` cleanup requires doctor, zero drift, and `--confirm`
