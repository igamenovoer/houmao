Houmao 3.1.0 adds managed Hermes workers and a browser terminal for live tmux sessions. Operators upgrading from 3.0.0 should review the changes to manual adoption and unattended launches below.

## Added

- **Managed Hermes workers.** Prepare Hermes v0.23.4 once per execution owner, then launch workers in `service` (the default), `tui`, or `headless` mode. Workers share the native gateway and keep separate profiles, credentials, and conversations. Use `--reasoning-level` to select effort in all three modes. [Owner Setup](https://igamenovoer.github.io/houmao/reference/run-phase/hermes-owner-setup/) · [Managed Hermes](https://igamenovoer.github.io/houmao/reference/run-phase/hermes-modes/)
- **Browser access to managed tmux sessions.** Open a live terminal from the owner-local gateway dashboard or request a one-time link with `gateway terminal-entry`. The default link is read-only. Interactive access follows the gateway’s administrator policy, and a keyed gateway requires an enrolled administrator. [Gateway Terminal Access](https://igamenovoer.github.io/houmao/reference/gateway/operations/access/#open-a-managed-tmux-terminal)
- **Named models for test fixtures.** Contributors can select a model by pool key or assign different models to agent slots. The same pool entry can drive raw-client and manager tests. [Fixture Guide](https://github.com/igamenovoer/houmao/blob/v3.1.0/scripts/agents/test-fixtures/README.md#select-models-for-instructional-tests)

## Upgrade Notes

- **Manual tmux adoption has been removed.** Before upgrading, use the owning Houmao version to detach the gateway from any session adopted with `agents self join`. Detaching leaves the provider running. For continued managed control, launch a fresh agent with `houmao-mgr project agents launch`. [Migrating Adopted Sessions](https://igamenovoer.github.io/houmao/reference/run-phase/session-lifecycle/#upgrading-from-manual-session-adoption)
- **Unattended launches now reject conflicting permission settings.** Select `as_is` for custom native approvals or a restricted sandbox, including DSH’s `workspace-write` setting. On relaunch, Houmao checks for conflicts before replacing the running agent. [Launch Policy](https://igamenovoer.github.io/houmao/reference/build-phase/launch-policy/)

## Installation

```bash
uv tool install 'houmao==3.1.0'
npx skills add https://github.com/igamenovoer/houmao-skills#v3.1.0
```

[Compare v3.0.0 and v3.1.0](https://github.com/igamenovoer/houmao/compare/v3.0.0...v3.1.0)
