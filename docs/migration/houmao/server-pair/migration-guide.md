# Migration Guide

This guide is for operators and developers moving from:

- `cao-server`
- `cao`

to the Houmao-managed replacement pair:

- `houmao-server`
- `houmao-srv-ctrl`

## 1. Understand The Support Boundary

The supported migration target is the pair:

```text
houmao-server + houmao-srv-ctrl
```

Do not plan around mixed deployments such as:

- `houmao-server + cao`
- `cao-server + houmao-srv-ctrl`

Those combinations are outside the supported contract of this implementation.

## 2. Keep `cao` Installed

`houmao-srv-ctrl` delegates most CAO-compatible commands to the installed `cao` executable in v1, so the migration still requires `cao` to be present on `PATH`.

You are moving the public authority to Houmao, not removing CAO internals from the shallow-cut implementation yet.

## 3. Start `houmao-server`

Typical local start:

```bash
pixi run houmao-server serve --api-base-url http://127.0.0.1:9889
```

Optional controls:

```bash
pixi run houmao-server serve \
  --api-base-url http://127.0.0.1:9889 \
  --runtime-root /tmp/houmao-runtime \
  --watch-poll-interval-seconds 1.0 \
  --recent-transition-limit 24
```

What changes when you do this:

- `houmao-server` becomes the public HTTP authority
- the child `cao-server` is supervised internally by `houmao-server`
- live terminal tracking becomes server-owned and runs from direct tmux/process observation
- the child listener stays internal and is derived as `public_port + 1`
- server-owned state is written under `<runtime-root>/houmao_servers/<host>-<port>/`
- pair-targeted installs go through `houmao-srv-ctrl install --port <public-port>` instead of direct `HOME` mutation

## 4. Switch Service-Management Commands To `houmao-srv-ctrl`

Replace direct `cao` usage with `houmao-srv-ctrl`.

Examples:

```bash
pixi run houmao-srv-ctrl info
pixi run houmao-srv-ctrl init
pixi run houmao-srv-ctrl install gpu-kernel-coder
pixi run houmao-srv-ctrl install gpu-kernel-coder --provider codex --port 9889
pixi run houmao-srv-ctrl launch --agents gpu-kernel-coder --provider codex --headless
pixi run houmao-srv-ctrl shutdown --all
```

If your workflow depends on the familiar `cao` command name, shell aliasing remains viable as long as the alias resolves to `houmao-srv-ctrl` in the supported pair.

Use the additive `--port` form when you are intentionally targeting a running Houmao pair instance. That path routes install through the selected `houmao-server`, so the child-managed CAO home stays an internal implementation detail instead of a caller-computed path.

## 5. Use Houmao Inspection Commands

After switching, inspect state through `houmao-server` instead of reading only raw CAO state.

Examples:

```bash
pixi run houmao-server health
pixi run houmao-server current-instance
pixi run houmao-server sessions list
pixi run houmao-server sessions get cao-gpu
pixi run houmao-server terminals state abcd1234
pixi run houmao-server terminals history --limit 20 abcd1234
```

These commands expose Houmao-owned views such as:

- additive health metadata
- current server instance details
- explicit transport/process/parse state for tracked sessions
- derived operator-facing live state and stability metadata
- bounded in-memory recent transitions

## 6. Understand What `launch` Does Differently Now

`houmao-srv-ctrl launch` still delegates the underlying launch to `cao`, but successful launches now also trigger Houmao-owned follow-up work:

- register the launched session in `houmao-server`
- materialize a runtime-owned session root
- write a manifest with `backend = "houmao_server_rest"`
- publish compatibility pointers when transitional registry flows need them
- let `houmao-server` rediscover and continuously track the tmux-backed session from its registration seed

This is the key migration seam that lets later runtime, registry, gateway, and mailbox flows treat the session as Houmao-owned rather than as raw CAO state.

## 7. Runtime Sessions Now Persist As `houmao_server_rest`

When a session is launched through the Houmao server pair and runtime artifacts are materialized, the persisted session identity is:

```text
backend = "houmao_server_rest"
```

That means:

- the manifest points at `houmao-server`
- runtime follow-up control should use the persisted Houmao server identity
- the session should not be mentally modeled as plain `cao_rest` anymore

## 8. Roll Out In A Safe Sequence

Recommended migration order:

1. Start `houmao-server` on the CAO-facing public base URL you want to own.
2. Replace operator command usage from `cao` to `houmao-srv-ctrl`.
3. Verify `houmao-server health` and `houmao-srv-ctrl info`.
4. If needed, install agent profiles through `houmao-srv-ctrl install --port <public-port> ...`.
5. Launch one new session through `houmao-srv-ctrl launch`.
6. Inspect the session through `houmao-server sessions` and `houmao-server terminals`.
7. Move runtime and follow-up tooling toward the persisted `houmao_server_rest` artifacts.

## 9. Roll Back If Needed

Rollback remains straightforward because the Houmao server pair is an additive adoption path in this repository:

- stop `houmao-server`
- stop using `houmao-srv-ctrl`
- return operators to `cao-server + cao`

What you should not do during rollback is keep one side on Houmao and the other side on raw CAO. The supported story is pairwise in both directions:

- adopt the pair together
- roll back from the pair together

## Related References

- [Houmao Server Pair](../../../reference/houmao_server_pair.md)
- [Houmao Server Filesystem Reference](../../../reference/system-files/houmao-server.md)
- [What We Tested](tested.md)
