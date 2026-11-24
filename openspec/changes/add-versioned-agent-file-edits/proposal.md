# Proposal

## Why

Peers can currently change an agent's skill and plugin files outside its execution controls. A versioned draft lets an authorized peer edit while the target works, then publish one complete revision at a boundary that protects the running agent.

## What Changes

- Expose owner-defined logical file mounts through the target gateway. Authorized peers can open a draft, edit files, inspect the diff, and save a Git commit without changing active files.
- Add an explicit push operation that compares the expected published revision, takes target maintenance, and publishes and activates the selected commit. Return a durable receipt with separate published and effective revision evidence.
- Use the shared gateway policy for mount access. Grant specific operations to an enrolled logical agent independently of its running context. Named admins and callers admitted through a valid empty roster can use every supported file operation.
- Use Dulwich for Git history on the gateway host. Record the authenticated requester as author and the target gateway as committer. Keep the file client HTTP-based and make the mount contract extensible to other resource types.
- Deliver an owner-enabled private skills mount for qualified DSH Web agents first. Add scoped manager commands for the file workflow and use the common access commands to administer grants.

## Capabilities

### New Capabilities

- `gateway-versioned-file-edits` defines logical mounts, draft versions, guarded push, and recovery.

### Modified Capabilities

- `authenticated-gateway-access` applies the shared caller proof and target policy to versioned file operations.
- `managed-agent-control` coordinates versioned publication with ordinary owner and native execution.
- `houmao-mgr-agents-scope-cli` exposes the scoped file edit workflow using the common access commands.

## Impact

This change depends on `replace-gateway-access-with-pycasbin`. It adds a Dulwich dependency, owner-private revision and operation storage, typed gateway endpoints, scoped CLI commands, and a DSH Web companion adapter. The first implementation uses direct verified gateway HTTP. MCP and native-specific mounts, WebDAV, standard Git transport, and passive proxy routes can build on this contract in later changes.
