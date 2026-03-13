I will pick the user-home one-instance-per-subdir approach to store the shared registry data, our service instance will have a localhost url with specific port, and it will has a globally unique name, it has some associated "runtime_dir" that is out of the home dir (can be anywhere, it stores some per-instance states), it also has a associated tmux session with specific name (for windows, this will later become psmux name), now give me a design of shared registry


---
Here’s a design I’d use for your case.

The core idea is: **the filesystem is the registry**, but there is **no shared index file**. Each service instance owns exactly one subdirectory and only writes inside that subdirectory. That removes almost all inter-service write races. Put the registry under a **per-user persistent root**; conceptually this is “state,” not “runtime.” On Linux, XDG distinguishes persistent user state (`XDG_STATE_HOME`) from runtime files (`XDG_RUNTIME_DIR`), and `XDG_RUNTIME_DIR` is explicitly removed on logout/reboot, so it is the wrong place for a durable registry. If you want OS-native placement instead of a literal home-dotdir, `platformdirs.user_state_path(...)` is the right abstraction; it provides a user-specific state path across platforms. ([Freedesktop.org Specifications][1])

I would define one variable up front:

```text
REGISTRY_ROOT = absolute persistent per-user directory
```

Two sane defaults are:

```python
# strict "under home" default
Path.home() / ".myapp-registry" / "v1"

# better OS-native default
platformdirs.user_state_path("myapp", "MyOrg", ensure_exists=True) / "registry" / "v1"
```

Your per-instance `runtime_dir` stays separate and can point anywhere. If you ever need a default runtime area, `platformdirs.user_runtime_path(...)` is the cross-platform abstraction for a user runtime path. ([platformdirs][2])

I would not use the raw global service name directly as the directory name unless you tightly constrain it to short ASCII. For cross-platform safety, make the subdir name a deterministic hash of the logical name:

```text
instance_key = sha256(instance_name_utf8).hexdigest().lower()
INSTANCE_DIR = REGISTRY_ROOT / instance_key
```

That avoids problems with slashes, colons, reserved names, path length edge cases, and case-insensitive filesystems. The real human-meaningful name stays inside the JSON record.

The on-disk layout can stay very small:

```text
REGISTRY_ROOT/
  v1/
    8f6c1f9d...e2a4/
      record.json
      .tmp-<random>    # transient during publish only
    a19b7c4e...91d0/
      record.json
```

I recommend **one authoritative file per instance dir**:

* `record.json` — the current published record
* temporary files only during atomic updates

No shared `index.json`, no shared SQLite, no per-registry lock.

A good `record.json` shape is:

```json
{
  "schema": "com.myorg.local-registry/v1",
  "instance_name": "agent://node-17/service-abc",
  "instance_key": "8f6c1f9d5a4c...",
  "generation_id": "0c24f7aa-3dc5-4ce1-9b4c-0f0ff5d91f63",

  "state": "ready",
  "published_at": "2026-03-13T23:45:01Z",
  "heartbeat_at": "2026-03-13T23:45:11Z",
  "lease_ttl_s": 30,
  "lease_expires_at": "2026-03-13T23:45:41Z",

  "endpoint": {
    "transport": "http-tcp",
    "url": "http://127.0.0.1:48123",
    "host": "127.0.0.1",
    "port": 48123
  },

  "runtime": {
    "dir": "/abs/path/or/C:\\abs\\path",
    "kind": "instance-runtime"
  },

  "mux": {
    "kind": "tmux",
    "session_name": "svc-abc"
  },

  "process": {
    "pid": 12345
  },

  "meta": {
    "service_type": "worker",
    "tags": ["gpu", "agent"]
  }
}
```

A few important choices in that schema:

* `generation_id` changes on every process start. This distinguishes “same logical instance name, new process” from an old stale publisher.
* `lease_expires_at` is what readers trust, not directory existence.
* `endpoint.url` should be the exact client URL to use. Do **not** make readers reconstruct it from name + port. Also prefer publishing `127.0.0.1` or `[::1]` explicitly instead of plain `localhost`, because resolution behavior can vary.
* `runtime.dir` and `mux.session_name` are metadata for tooling/ops, not the discovery authority.

For publishing, use **write-temp-then-replace** inside the same instance directory. Python documents `tempfile` as working on all supported platforms, and `os.replace()` as the cross-platform overwrite operation; it also notes that rename/replace may fail across filesystems, so the temp file must be created in the **same directory/filesystem** as `record.json`. ([Python documentation][3])

So the publish algorithm is:

1. Ensure `INSTANCE_DIR` exists.
2. Build the full new record in memory.
3. Create a temp file inside `INSTANCE_DIR`.
4. Write full JSON to temp file.
5. Optionally `fsync()` the temp file if you care about crash durability.
6. `os.replace(tmp, INSTANCE_DIR / "record.json")`.

That gives readers a clean “old record or new record” view, with no partial JSON exposed. Python explicitly recommends `replace()` when you want cross-platform overwriting of the destination. ([Python documentation][4])

For Python, I’d implement the write path roughly like this:

```python
import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone


def now_utc():
    return datetime.now(timezone.utc)


def instance_key(name: str) -> str:
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def write_record_atomic(instance_dir: Path, record: dict) -> None:
    instance_dir.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", dir=instance_dir)
    tmp_path = Path(tmp_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(record, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            f.write("\n")
            f.flush()
            # os.fsync(f.fileno())  # enable if you want stronger crash durability

        os.replace(tmp_path, instance_dir / "record.json")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
```

For lifecycle, use a lease model:

* heartbeat every `lease_ttl_s / 3`
* readers treat an entry as live only when:

  * `state == "ready"`
  * `lease_expires_at > now`
  * JSON parses
  * `instance_key` matches the directory name
  * optional: the health URL answers

On clean shutdown, the service should best-effort either delete `record.json` or publish `state="stopping"` with a very short expiry and then delete it. But readers must **not** depend on graceful cleanup; stale-entry handling must rely on the lease.

For lookup, I’d support exactly two operations:

```text
resolve(instance_name) -> one record or None
list_active() -> all non-stale ready records
```

`resolve(instance_name)` is direct and fast:

1. compute `instance_key = sha256(name)`
2. open `REGISTRY_ROOT / instance_key / record.json`
3. validate `record["instance_name"] == input_name`
4. validate freshness

That means known-name discovery is **O(1)** and never needs to scan sibling directories.

The only real race left in this design is **two processes accidentally using the same logical instance name**. Different instance names do not contend, because they never touch the same subdirectory. To handle same-name contention, I would use a conservative ownership rule:

* on startup, read any existing `record.json`
* if it exists and is still fresh, fail startup
* otherwise publish a new record with a new `generation_id`
* on each heartbeat, the process may re-read `record.json`; if the on-disk `generation_id` no longer matches its own, it stops publishing and exits or demotes itself

That is usually enough if duplicate names are a bug, not a normal operating mode. If you later decide you need hard exclusion for same-name startup, add a per-instance lock file in that one subdirectory only; you still do not need a global registry lock.

I would also add one janitor command:

```text
registry gc
```

It removes instance dirs whose records are expired beyond a grace period, for example 24 hours. Since your registry root is persistent, stale subdirs may remain after crashes or reboot, and that is fine. The XDG spec’s distinction is helpful here: persistent registry metadata belongs in user state, while volatile runtime artifacts belong in runtime paths. ([Freedesktop.org Specifications][1])

My final recommended contract is:

* one persistent per-user root
* one hashed subdir per logical instance name
* one authoritative `record.json` per instance
* atomic replace on updates
* `generation_id` per process start
* lease/expiry for liveness
* no global index
* no shared writable file
* `runtime_dir` and `tmux/psmux` info stored as metadata only

If you want, I can turn this into a small Python module with `publish()`, `heartbeat()`, `resolve()`, `list_active()`, and `gc()`.

[1]: https://specifications.freedesktop.org/basedir/latest/ "XDG Base Directory Specification"
[2]: https://platformdirs.readthedocs.io/en/latest/api.html "API - platformdirs"
[3]: https://docs.python.org/3/library/tempfile.html "tempfile — Generate temporary files and directories — Python 3.14.3 documentation"
[4]: https://docs.python.org/3/library/os.html "os — Miscellaneous operating system interfaces — Python 3.14.3 documentation"
