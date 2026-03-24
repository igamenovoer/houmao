# CAO Server

This page is historical reference only.

The standalone CAO launcher workflow is retired:

- `houmao-cao-server`
- `python -m houmao.cao.tools.cao_server_launcher`

Those entrypoints now fail fast with migration guidance to:

```text
houmao-server + houmao-srv-ctrl
```

## Why This Page Still Exists

Older tests, migration notes, and cleanup tasks may still refer to the legacy standalone launcher layout under:

```text
<runtime-root>/cao_servers/<host>-<port>/
```

That layout is no longer part of the supported pair contract. It is documented only so legacy artifacts can be recognized and cleaned up safely when encountered.

## Legacy Layout Summary

Historical standalone launcher roots used:

```text
<runtime-root>/cao_servers/<host>-<port>/
  launcher/
    cao-server.pid
    cao-server.log
    ownership.json
    launcher_result.json
  home/
```

That path family belonged to the retired standalone launcher and should not be used for new Houmao pair deployments.

## Related References

- [Houmao Server Pair](../houmao_server_pair.md)
- [Houmao Server Filesystem Reference](houmao-server.md)
