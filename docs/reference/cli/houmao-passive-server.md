# houmao-passive-server

Registry-first passive server for distributed agent coordination.

`houmao-passive-server` is a lightweight FastAPI application that discovers agents from the shared filesystem registry and provides coordination, observation, and proxy services on top of them. Unlike `houmao-server`, this server has no legacy compatibility layer, no child process supervision, and no registration-backed session admission. It is designed as a clean replacement aligned with the distributed-agent architecture.

## Synopsis

```
houmao-passive-server [OPTIONS] COMMAND [ARGS]...
```

## Commands

### `serve`

Start the passive server.

```
houmao-passive-server serve [OPTIONS]
```

**Options:**

| Option | Default | Description |
|---|---|---|
| `--host TEXT` | `127.0.0.1` | Host address to bind the server to. |
| `--port INT` | `9891` | Port to listen on. |
| `--runtime-root PATH` | | Root directory for runtime state and the shared agent registry. |
