# Agent Identity

Houmao uses `agent_id` as an immutable, globally unique logical identity. UUIDs are the default for new agents. Friendly names, mail addresses, provider conversation IDs, session IDs, and tmux handles are separate fields. Two observations of the same ID refer to the same agent. Houmao does not detect accidental ID collisions, and an ID does not grant access to an agent or mailbox.

## Creating an Agent

The maintained launch commands accept an optional `--agent-id-mode uuid|name-hash`. Omitting it generates a UUID unless `--agent-id` supplies an opaque ID. Supplying both options is an error, including an explicit `--agent-id-mode uuid` with an ID.

```bash
# A new UUID-backed agent; another launch named alice receives a different ID.
pixi run houmao-mgr project agents launch --profile researcher --name alice

# An explicit stable identity chosen by the caller.
pixi run houmao-mgr project agents launch --profile researcher --name alice --agent-id team-alice

# Opt-in local convenience: preserve the existing normalized-name hash algorithm.
pixi run houmao-mgr project agents launch --profile researcher --name alice --agent-id-mode name-hash
```

In `name-hash` mode, the caller guarantees name uniqueness. Repeating the same normalized name produces the same ID and addresses the same logical agent. Names are case sensitive. A name lookup can be ambiguous when distinct IDs share a friendly name; select the returned `agent_id` explicitly for later operations.

A supported launch establishes the managed identity. Subsequent managed relaunches preserve it.

## Reusing an Agent or a Template

A brain built without identity inputs is a reusable template. It does not contain an agent identity. Starting a new agent from that template resolves its identity before runtime or mailbox publication. Named brain builds, supplied IDs, and explicit ID modes create an identity-bearing brain. Such a brain retains its ID across launch, rename, and home reuse; it cannot generate or accept a different ID. Build an identity-free template to create another logical agent.

Managed launch resolves the ID before brain materialization and prompt rendering, then passes the same ID into runtime startup. The typed `AgentIdentityCreation` input provides the same decision for Python callers. UUID, `name-hash`, and `supplied` provenance is diagnostic metadata; callers still treat the resulting ID as opaque.

Use a persisted ID with `--reuse-home` or `--force`. Explicit `--agent-id-mode name-hash` can select an existing identity in a deliberately name-based local setup. An ordinary friendly name does not select a preserved home under UUID defaults.

```bash
pixi run houmao-mgr project agents launch --profile researcher --name alice --agent-id <persisted-id> --reuse-home
pixi run houmao-mgr agents single --agent-id <persisted-id> relaunch
```

Resume, relaunch, discovery, manifest serialization, and registry refresh validate the stored identity. They never hash a name or generate a UUID to repair a missing durable ID. Invalid records fail explicitly so that another logical agent cannot silently inherit sessions, history, or mailbox ownership.

## Mail Addresses

Offline and online mail addresses bind to the same `agent_id`. The canonical mail identity uses the configured online address first, otherwise offline, otherwise none. Connectivity failures do not change this identity. Attaching or detaching mail never changes the internal agent ID, and canonical mail precedence never chooses a delivery channel.
