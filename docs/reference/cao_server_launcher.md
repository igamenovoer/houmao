# CAO Server Launcher

The standalone CAO launcher surface is retired.

The following entrypoints now fail fast with migration guidance and exit code `2`:

- `houmao-cao-server`
- `python -m houmao.cao.tools.cao_server_launcher`

Use the supported pair instead:

```text
houmao-server + houmao-mgr
```

Typical replacement flow:

```bash
pixi run houmao-server serve --api-base-url http://127.0.0.1:9889
pixi run houmao-mgr install projection-demo --provider codex --port 9889
pixi run houmao-mgr launch --agents projection-demo --provider codex --port 9889
```

This page remains only as a retirement note. The standalone launcher is no longer a supported operator workflow.

## Related References

- [Houmao Server Pair](houmao_server_pair.md)
- [Legacy CAO Server Layout](system-files/cao-server.md)
