## Context

`houmao-passive-server` has broad unit coverage, but the AG-UI workbench depends on the real process-level behavior of the passive server: it must start through the packaged CLI, answer HTTP requests, discover live registry-backed agents, and proxy gateway status for discovered targets. The existing `tests/manual/` scripts validate other live-runtime paths, but there is no small passive-server-focused manual suite.

The proposed scripts are manual smoke tests, not CI tests. They should be easy to run from the repository with `pixi run python tests/manual/<script>.py`, use isolated temporary roots, and avoid real provider calls unless a future script explicitly opts into them.

## Goals / Non-Goals

**Goals:**

- Validate the maintained `houmao-passive-server serve` CLI with a real subprocess.
- Validate the HTTP route families required by the AG-UI workbench discovery path.
- Validate registry discovery with real tmux liveness filtering and strict registry records.
- Validate gateway proxy forwarding using a fake gateway instead of a real agent gateway.
- Keep scripts deterministic, cleanup-safe, and explicit about prerequisites.

**Non-Goals:**

- Do not add new passive-server API routes or runtime behavior.
- Do not run real LLM turns as part of the default passive-server manual suite.
- Do not make these manual scripts part of the default unit-test command.
- Do not require the AG-UI workbench or browser automation for these scripts.

## Decisions

1. Use three separate scripts instead of one large scenario runner.

   Separate scripts keep failures localized: lifecycle failures, registry discovery failures, and gateway proxy failures imply different root causes. This also lets operators rerun only the area that matters during GUI debugging.

2. Start the passive server as a real CLI subprocess.

   The lifecycle and HTTP scripts should invoke `pixi run houmao-passive-server serve` rather than importing `create_app()` directly. Unit tests already cover the in-process FastAPI contracts; these manual tests should catch packaging, CLI wiring, uvicorn startup, runtime-root selection, and subprocess shutdown issues.

3. Use isolated runtime, registry, mailbox, and job roots.

   Each script should create a temporary working directory and set `HOUMAO_GLOBAL_RUNTIME_DIR`, `HOUMAO_GLOBAL_REGISTRY_DIR`, `HOUMAO_GLOBAL_MAILBOX_DIR`, and `HOUMAO_LOCAL_JOBS_DIR` for child processes. This prevents manual validation from reading or mutating a developer's active Houmao state.

4. Seed discovery with strict registry helpers plus real tmux sessions.

   The discovery script should create a real tmux session and publish a `ManagedAgentRegistryRecordV3` through the existing registry storage helper. It should also publish or write at least one stale/dead record to prove the passive server does not list records whose tmux session is absent or whose lease is invalid.

5. Use a fake HTTP gateway for proxy validation.

   The gateway proxy script should bind a local fake gateway implementing only the route shapes it validates, then publish gateway coordinates in the registry record. This verifies passive-server resolution and `GatewayClient` forwarding without needing a full managed agent or real provider credentials.

## Risks / Trade-offs

- `tmux` missing on the host -> scripts fail with a clear prerequisite error before starting the scenario.
- Port collisions -> scripts bind or select free local ports instead of assuming `9891`.
- Cleanup failure leaves subprocesses or tmux sessions alive -> scripts should register `finally` cleanup for server subprocesses, fake gateway threads/processes, temp directories, and created tmux sessions.
- Fake gateway is not a complete gateway -> the script should validate only routes it implements and state that broader gateway behavior remains covered by unit and integration tests.
- Manual scripts can drift from API contracts -> scripts should parse JSON and assert key fields rather than matching loose text output.
