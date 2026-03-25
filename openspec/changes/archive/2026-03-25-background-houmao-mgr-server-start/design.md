## Context

`houmao-mgr server start` is the documented pair-native entrypoint for starting `houmao-server`, but its implementation currently just calls the shared `run_server(...)` path directly. In practice that means it behaves like `houmao-server serve`: the process stays attached to the current terminal, startup success is inferred from uvicorn logs, and operators need a second shell to continue with `houmao-mgr server status`, `agents launch`, or other follow-up commands.

The underlying server runtime already publishes enough ownership state for a better operator-facing start workflow. `HoumaoServerConfig` derives a stable `server_root` and run-state paths, and `HoumaoServerService.startup()` writes `current-instance.json` plus a pid file under that root once the process is live. That makes it feasible for `houmao-mgr server start` to become a launcher-style command that starts the server in the background by default, waits for health, and prints a structured startup result.

Constraints:

- Preserve the existing shared uvicorn startup path so `houmao-mgr server start` and `houmao-server serve` still run the same actual server runtime.
- Keep `houmao-server serve` available as the direct foreground server entrypoint.
- Avoid a shell- or Pixi-specific solution; the managed CLI should be able to spawn the detached child from the current Python environment.
- Keep failure signaling explicit. A detached start that silently exits is worse than the current foreground behavior.

## Goals / Non-Goals

**Goals:**

- Make `houmao-mgr server start` detached-by-default.
- Add `--foreground` so operators can explicitly request the current foreground-blocking behavior.
- Make detached start print one structured startup result with the resolved URL, success state, pid/runtime metadata when available, and a clear detail message.
- Bound detached startup by an explicit health wait so the command either returns a successful start result or a clear unsuccessful result.
- Reuse an already-running healthy `houmao-server` instance on the requested base URL instead of blindly spawning duplicates.

**Non-Goals:**

- Changing `houmao-server serve` semantics or making it detached by default.
- Introducing a new long-running launcher daemon or supervisor process beyond the actual server child.
- Changing the `houmao-server` HTTP API surface.
- Designing a generic backgrounding framework for unrelated `houmao-mgr` commands.

## Decisions

### D1: `houmao-mgr server start` gets two execution modes

**Decision:** The `server start` command will support:

- default detached mode: spawn a child server process, wait for health, print startup status, then exit
- explicit foreground mode via `--foreground`: run the existing shared `run_server(...)` path directly in the current process

`houmao-server serve` remains the direct server binary for foreground use and keeps its current behavior.

**Rationale:** This satisfies the requested operator UX without changing the underlying server binary contract. The pair-native command becomes convenient for normal use, while `--foreground` and `houmao-server serve` still cover debugging and log-tail workflows.

**Alternatives considered:**

- Change `houmao-server serve` itself to detach by default: rejected because it would blur the separation between the server binary and the pair-management CLI.
- Always detach and remove foreground behavior: rejected because foreground startup is still useful for debugging and development.

### D2: Detached mode spawns one child that runs the same foreground startup path

**Decision:** Detached `houmao-mgr server start` will spawn a subprocess in a new session whose command line resolves back into the same CLI entrypoint with `server start --foreground` plus the resolved startup flags.

The parent launcher process will not call `run_server(...)` directly. The child process will own the actual uvicorn server runtime, and the parent will only manage child creation, startup waiting, and result reporting.

**Rationale:** This keeps one canonical server runtime path and avoids having two partially divergent startup implementations. It also matches the test helper pattern already used in integration tests, which invokes the `houmao-mgr` CLI entrypoint in a subprocess.

**Alternatives considered:**

- Spawn `houmao-server serve` instead of `houmao-mgr server start --foreground`: viable, but less direct for sharing future `houmao-mgr`-specific startup affordances.
- Fork the current process and daemonize manually: rejected as unnecessarily low-level and harder to keep portable and testable.

### D3: Detached start is health-check-first and reuse-aware

**Decision:** Before spawning a new child, detached `houmao-mgr server start` will probe the requested base URL. If a reachable `houmao-server` is already healthy there, the command will return a successful startup result that reports the existing instance instead of attempting a second bind.

If nothing healthy is reachable, the command spawns the child and waits until either:

- the server health route responds with `houmao_service = "houmao-server"`, or
- the child exits / the startup deadline expires

**Rationale:** Reuse-aware behavior avoids duplicate listeners and gives operators a predictable result when they rerun `server start`. A bounded startup wait is required so detached mode never silently “succeeds” while the child immediately dies.

**Alternatives considered:**

- Always spawn and let bind failure surface from the child: rejected because repeated operator `start` calls would be noisy and less informative.
- Fire-and-forget without waiting for health: rejected because it cannot reliably report whether startup succeeded.

### D4: Detached mode writes server child output to server-owned log files

**Decision:** The detached child’s stdout/stderr will be redirected into stable files under `config.logs_dir`, using explicit server-owned names such as `houmao-server.stdout.log` and `houmao-server.stderr.log`.

The detached startup result will include log paths when startup fails before health so operators can inspect the child output immediately.

**Rationale:** Foreground uvicorn output is useful during debugging, but detached mode needs durable log destinations or else startup failures become opaque. The server root already has a log directory contract, so the launcher should reuse it.

**Alternatives considered:**

- Discard detached stdout/stderr: rejected because it makes failure diagnosis unnecessarily hard.
- Print child logs inline from the parent: rejected because the launcher should terminate quickly once the startup result is known.

### D5: Startup result uses the existing JSON-emission style

**Decision:** Detached `houmao-mgr server start` will emit one structured JSON payload via the existing `emit_json(...)` helper. The payload should include, at minimum:

- `success`
- `running`
- `mode` (`background` or `foreground`)
- `api_base_url`
- `detail`

When available, it should also include:

- `pid`
- `server_root`
- `started_at_utc`
- `current_instance`
- `log_paths`
- `reused_existing`

Foreground mode does not need to emit the detached startup payload before blocking; it preserves direct attached startup behavior.

**Rationale:** The surrounding `houmao-mgr` server lifecycle commands already use JSON output. Reusing that shape keeps the command automation-friendly and easy to inspect from scripts.

**Alternatives considered:**

- Human-formatted text only: rejected because the rest of the CLI already leans on structured JSON payloads for lifecycle commands.

## Risks / Trade-offs

- [Risk] Detached start introduces launcher complexity around subprocess environment, file descriptors, and startup polling.
  -> Mitigation: keep detached mode narrowly scoped to `houmao-mgr server start`, and keep the actual server runtime path shared with foreground mode.

- [Risk] A stale or foreign process could already be listening on the requested port.
  -> Mitigation: validate that the reachable service is actually `houmao-server` before treating it as reusable; otherwise fail with the existing mixed-pair guidance.

- [Risk] Startup may succeed after the launcher’s wait budget expires, producing a false negative.
  -> Mitigation: use a reasonable bounded wait and report log paths plus the target URL so operators can inspect or retry intentionally.

- [Risk] Changing the default from foreground to background is behaviorally breaking for operators who depended on the current blocking semantics.
  -> Mitigation: provide explicit `--foreground`, update docs/examples, and keep `houmao-server serve` unchanged.

## Migration Plan

1. Add detached/foreground execution branching to `houmao-mgr server start`.
2. Add startup result modeling and health-wait helpers for the detached path.
3. Update CLI tests to assert:
   - default detached start returns a success payload and does not block
   - `--foreground` preserves attached startup
   - failed detached start returns an unsuccessful result
4. Update docs/examples so pair-managed startup uses the new default and explains `--foreground`.

## Open Questions

- Whether detached start should expose a user-configurable startup wait flag immediately or rely on a fixed internal timeout for v1.
- Whether the startup result should include both split stdout/stderr log paths or one combined launcher log path. The repo already uses split names in demo artifacts, so that is the likely default unless implementation friction is high.
