# Logs

## Purpose
Record development sessions and outcomes (including failed attempts and lessons learned).

## Layout

`context/logs/` is organized by intent:

- `runs/`: logs produced while running, launching, probing, validating, or otherwise executing something concrete
- `explore/`: idea exploration, architecture notes, discussion artifacts, and analysis logs
- `code-review/`: review reports and code-reading findings kept in a dedicated bucket

Use timestamped names inside the appropriate bucket.

## Historical Snapshots
Some log files may be copied into this directory to satisfy archived OpenSpec
references. Treat them as historical snapshots, not continuously updated logs.
