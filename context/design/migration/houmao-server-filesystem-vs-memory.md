# Houmao Server Filesystem Vs Memory Ownership

## Purpose

This note records the intended persistence boundary for `houmao-server` adoption. The goal is to avoid treating every current filesystem artifact as equally canonical once a resident `houmao-server` owns the live control plane.

The rule is simple:

- Durable content, pointer layers, tool-owned working state, and logs stay filesystem-authoritative by design.
- Some current filesystem artifacts are only transitional compatibility bridges. They stay on disk in v1, but the future architectural authority moves into `houmao-server`.
- Hot control-plane state that describes what is live right now should become `houmao-server` memory over time.
- Filesystem copies of memory-primary state may continue to exist for compatibility, debugging, or migration, but they should not define the long-term control-plane authority.

## Filesystem-Authoritative By Design

The following current artifacts should remain canonical on disk even after `houmao-server` matures:

- `~/.houmao/runtime/homes/<home-id>/`
- `~/.houmao/runtime/manifests/<home-id>.yaml`
- `<runtime-root>/sessions/<backend>/<session-id>/`, especially `<session-root>/manifest.json`
- `~/.houmao/mailbox/...`
- `<working-directory>/.houmao/jobs/<session-id>/`
- Houmao-owned server roots that `houmao-server` manages under the Houmao home anchor
- log files such as `houmao-server.log`, child `cao-server` logs, and watch history logs

Why these stay on disk:

- Runtime homes and manifests are durable launch inputs and rebuildable runtime artifacts, not hot server state.
- Session roots and manifests are durable resume and inspection records.
- Mailbox storage is already designed as a filesystem transport and should keep that contract.
- Workspace job directories are tool-side work products and scratch/output roots, not server memory.
- Houmao still needs on-disk server roots for runtime support files, logs, and opaque adapter-private storage.
- Logs are naturally file-backed operator and debug artifacts.

## Transitional Filesystem Compatibility State

The shared registry stays on disk in the first `houmao-server` version, but it is not meant to remain filesystem-first by design:

- `~/.houmao/registry/live_agents/<agent-id>/record.json`

Why registry is transitional instead of permanently filesystem-authoritative:

- v1 still needs the existing filesystem registry for compatibility and migration.
- The intended long-term discovery path is that agents and tools query `houmao-server` to find each other.
- Future work can add dedicated `houmao-server` discovery endpoints and let the server decide whether the backing store is still raw files, indexed cache, or something else.
- Keeping registry in this middle bucket prevents the current on-disk locator format from becoming the permanent discovery authority by accident.

## Opaque Internal Adapter Storage Under Houmao-Owned Roots

In the shallow CAO-backed `houmao-server` cut, the child `cao-server` may still need filesystem-backed support state such as an effective `HOME` and adapter-private files.

That state should be stored under Houmao-owned server roots rather than exposed as a separate user-facing CAO-home surface.

Design intent:

- users interact with Houmao-managed homes and server roots, not CAO-branded homes
- `houmao-server` decides what child-CAO storage is needed and what gets passed to the internal child process
- the detailed layout and contents of that child-adapter subtree are internal implementation detail, not a stable public filesystem contract

## Memory-Primary Under `houmao-server`

The following current artifacts should move under `houmao-server` memory ownership, with filesystem views retained only where compatibility or migration requires them:

- live session and terminal registries
- watch-worker bindings and latest reduced terminal state
- request queues and current owned-work bookkeeping
- gateway-like control-plane artifacts under `<session-root>/gateway/`, especially:
  - `state.json`
  - `queue.sqlite`
  - `events.jsonl`
  - `run/current-instance.json`
  - `run/gateway.pid`
  - `attach.json`
  - `desired-config.json`
- child-launch bookkeeping under Houmao-owned server roots, especially pid, ownership, and last-launch-result artifacts

Why these should become memory-primary:

- They describe the live control plane rather than durable content.
- A resident server already has these facts in memory and can publish them via HTTP without forcing the filesystem to be the primary synchronization channel.
- Treating them as memory-primary avoids freezing temporary compatibility files into permanent public contracts.
- It lets `houmao-server` replace CAO and gateway-style live coordination incrementally without rewriting durable artifacts such as manifests or mailbox state.

## Compatibility And Migration Guidance

In the first `houmao-server` version, filesystem mirrors for memory-primary state are still acceptable when needed for compatibility with existing tooling or debugging habits. Those mirrors should follow these rules:

- They are generated views of server-owned live state, not the source of truth.
- New features should prefer `houmao-server` HTTP APIs and in-memory authority instead of adding more filesystem-first live-control contracts.
- Future cleanup may stop reading some compatibility mirrors even if the server still writes them for a transition period.
- Durable filesystem contracts such as session manifests, mailbox, job roots, and logs should continue to be read and written as first-class artifacts.
- Shared registry files should be treated as a compatibility bridge in v1, while new discovery features should target `houmao-server` query APIs instead of expanding direct raw-file lookup.
- Child-adapter files that exist only because the internal `cao-server` needs them should remain opaque and Houmao-managed rather than becoming user-facing filesystem contracts.

## Practical Adoption Rule

When deciding whether a current path belongs in the future architecture, ask:

1. Is this path durable content, tool-owned data, or a log? Keep it filesystem-authoritative.
2. Is this path a current compatibility bridge that should later be surfaced through `houmao-server` queries? Keep it on disk for now, but do not treat the file layout as the future authority.
3. Is this path mainly describing which worker, queue item, pid, or request is live right now? Move it toward `houmao-server` memory and keep any file only as a compatibility or debug view.

That split keeps the future architecture shallow where it should be shallow, but still moves the live control plane under Houmao ownership instead of preserving CAO-era filesystem coordination forever.
