# CAO Server

This page is historical reference only.

The standalone CAO launcher workflow has been removed:

- `houmao-cao-server`
- `python -m houmao.cao.tools.cao_server_launcher`

Those entrypoints are no longer packaged. Use the maintained manager and passive-server surfaces instead:

```text
houmao-mgr + houmao-passive-server
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

- [Passive Server API](../cli/houmao-passive-server.md)
- [Retired Houmao Server Filesystem Notes](houmao-server.md)
