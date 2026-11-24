# Design

## Context

The runtime currently captures an admitted execution socket, an explicit tmux scope, the enclosing `$TMUX` socket, or the native default. It saves the concrete socket in `manifest.json` and restores it on subsequent operations. Managed launch already preflights the target before force takeover, and tmux session creation already has a shared adapter and a curated startup environment. Fixture preparation currently pins a per-run socket through a PATH shim. See [the proposal](proposal.md) for the motivation.

## Goals and Non-Goals

Resolve a launch selector once in the execution owner’s context and carry its socket and startup permission through session creation. Use the same resolution logic for managed births and fixture-owned raw sessions. Executor admission, registry-based peer discovery, and the passive server’s authority over its own launches remain separate concerns.

## Decisions

### Store One Typed Selector in Launch Posture

Add an optional `defaults.posture.tmux` block to the shared project launch-profile model. The block holds `server` and, for `socket`, `socket_path`.

```yaml
defaults:
  posture:
    tmux:
      server: socket
      socket_path: /run/user/1000/research.sock
```

Use `--tmux-server` and `--tmux-socket-path` for profile authoring and one-shot project launches. Profile `set --clear-tmux-server` removes the block. Patch or override the block as a whole so an earlier `socket_path` cannot leak into a different mode. Keep normal add and patch omission semantics and render the same block in the compatibility projection. Keeping the selector in typed posture makes it available to owner-side validation before provider environment construction.

### Resolve the Birth Once Before Takeover

Resolve the direct launch override first, then the stored selector, then the existing execution scope, enclosing `$TMUX`, and native fallback. An admitted executor binding still constrains the selected socket. An incompatible choice fails in the owner context before force takeover or brain construction. Existing fixed-socket executor policies cannot admit `new`. Forward one-shot inputs through the owner request as data, and validate socket paths within that execution context.

| Mode | Concrete Socket | Startup Permission |
| --- | --- | --- |
| `user-default` | Native default for the execution account and its `TMUX_TMPDIR`, independent of the enclosing session | Start on first use if absent |
| `new` | Fresh, short socket in the owner’s private Houmao socket namespace | Start on first use if absent |
| `socket` | Supplied absolute owner-local path | Connect only |
| `houmao-default` | Address from the owner-scoped shared registry record | Start on first use if absent |

Pass the resolved socket and startup permission through the existing execution/runtime scope and common session creation path. All managed backends that create a tmux session should consume the same result. `--session-name` still supplies a session name on that server. Prepare socket directories only for admitted startup paths. Check reachability for `socket` before mutating a predecessor, and enforce connect-only at `new-session` dispatch. If the selected server disappears after preflight, return the startup failure with its socket. Guard a same-server force replacement when stopping the predecessor would shut down the selected server. Either preserve the live server through handoff or reject that replacement before teardown.

Use the existing libtmux dispatch for observations and the bounded startup adapter for curated process environments. Bind both to the resolved target and remove inherited `TMUX` and `TMUX_PANE` from child selection. Save the concrete socket and startup permission with the managed runtime binding. Later attach, prompt, observation, stop, and relaunch use the saved state, including after profile or default-record changes. A recreation permitted by the saved binding targets the saved socket. An unavailable active runtime remains an unavailable observation. A legacy manifest that has a socket keeps its current lifecycle behavior.

### Publish the Houmao Default as an Owner Record

Store a private, versioned record under the effective shared registry, in an owner-level namespace alongside agent records. The key identifies the observed execution host or container socket domain and effective OS UID. Project roots, agent identities, and project execution context IDs are excluded from the key. Store the key and absolute socket path, independent of server PID, liveness, and agent leases.

On first eligible launch, derive a stable short address beneath a verified owner-private socket directory. Derive the address from the owner and socket domain so separate empty fixture registry roots on the same owner converge. Publish the record atomically under a stable owner-key lock before the first session start. Revalidate an existing record under the lock and use the published address for concurrent launches and failed-start retries. Honor the owner’s registry-root override for record storage. Validate the socket namespace, file type, ownership, and permissions. Fail on unsafe records, conflicting socket filesystem objects, or an admitted executor binding that disallows the result.

Create a missing socket via the first session start at that address. An existing live server accepts additional sessions as usual. An existing record with a missing socket is ready for the next eligible start. Profile authoring, inspection, and cleanup perform no bootstrap. Agent stop removes only its verified session, and normal tmux exit when no sessions remain leaves the registry record available for reuse.

### Route Fixture Launch Through the Same Selection

Prepare a managed fixture profile with `houmao-default` by default, alongside its model and reasoning settings when present. Let managed launch select the socket from that profile. Read the socket from the returned manifest and record it with the fixture’s exact identity. Use the manager’s existing agent-ID lifecycle routes for managed fixture operations, including checks with the gateway detached.

Raw TUI and Web fixtures resolve the same mode in the fixture launch path and retain their concrete socket and owned session coordinates for follow-up. Verify the session’s run identity as well as its tmux coordinates, since a restarted server can reuse those IDs. Replace the default per-run PATH shim with explicit adapter binding. Start raw tmux with the same credential-free environment discipline as managed launch. Read provider inputs only in the owned child or Web supervisor from the existing private fixture state. Keep raw headless process-only and let passive API launches use the addressed server’s own socket policy.

Expose `fixture.py prepare --tmux-server new` for local isolated runs. Keep cross-server restrictions in test-owned shims, using the captured sockets to install restrictions before peer operations. For shared-default coverage, substitute a test-owned socket namespace in the resolver as well as using test-owned registry roots. Changing only the registry root still derives the execution owner’s ordinary default address. Other tmux fixture tests request isolated resources. A fixture retains its private home, runtime files, and registry directory in both modes. Cleanup verifies the captured agent or session before stopping it, including for failures after partial startup.

## Risks and Trade-offs

- A shared server exposes global tmux state to later sessions. Use a curated start environment, suppress session environment updates from the launch client, and keep provider credentials in private child inputs.
- A user-supplied server can exit between preflight and creation. An existing-only launch fails at the same socket if that happens. There is no implicit retargeting.
- Socket paths have a small platform limit. Keep the managed namespace short, validate before mutation when possible, and keep the socket outside the registry directory.

## Migration Plan

Profiles without a selection keep ordinary launch behavior. For fresh fixture runs that previously relied on a separate server, select `--tmux-server new` when preparing the run. Existing live fixture runs continue to use their recorded socket for status and cleanup. Document the changed fixture default together with the four project launch options and the test isolation procedure.
