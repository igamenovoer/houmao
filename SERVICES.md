# Local Development Services

This file records the services running for Houmao development in this workspace. Run the commands below from the project root, `/data/huangzhe/code/houmao`.

## Stalwart Mail Server

Stalwart was started and verified on 2026-11-13 for mailbox integration testing. It runs as `huangzhe` inside the Linux `aarch64` development workspace whose hostname is `main`.

| Item | Current Deployment |
| --- | --- |
| Container runtime | `udocker` 1.3.17, PRoot execution mode `P1` |
| Container name | `houmao-stalwart-dev` |
| Container ID | `2c00346d-ae0f-3f9e-8044-fa585194c4ae` |
| Image | `ghcr.io/stalwartlabs/stalwart:v0.15.5` |
| Runtime tools | `/home/huangzhe/.local/share/houmao-email-system/udocker-venv/` |
| Image cache and container filesystem | `/home/huangzhe/.local/share/houmao-email-system/udocker/` |
| Persistent service files | `dockers/email-system/.data/stalwart/` |
| Database | RocksDB, under `dockers/email-system/.data/stalwart/data/` |
| Lifecycle | Detached user process; start manually after the workspace stops or restarts |

This deployment runs Stalwart alone. The workspace has no Docker daemon or mounted Docker socket, and nested user namespaces are blocked, so the image runs through `udocker`. The [Docker Compose stack](dockers/email-system/README.md) describes a separate deployment that also includes Cypht and Postgres.

### Endpoints and Access

All listeners bind to `127.0.0.1` inside this workspace. To use the web UI from another machine, forward workspace port `10080` through your editor or SSH connection.

| Interface | Address |
| --- | --- |
| Web administration | <http://127.0.0.1:10080/login> |
| Management API | `http://127.0.0.1:10080/api` |
| JMAP session discovery | <http://127.0.0.1:10080/.well-known/jmap> |
| JMAP method calls | `http://127.0.0.1:10080/jmap/`, advertised by session discovery |
| HTTP liveness | <http://127.0.0.1:10080/healthz/live> |
| HTTP readiness | <http://127.0.0.1:10080/healthz/ready> |
| IMAP | `127.0.0.1:10143` |
| SMTP submission | `127.0.0.1:10587` |

The administrator login is `admin`. The regular test mailbox login is `test-agent`, with address `test-agent@example.test`. Passwords were generated locally and are stored in `dockers/email-system/.env`, with file permissions `0600`. Keep credential values out of tracked files, command arguments, and shared logs.

Use the session-discovery URL for Houmao's `StalwartJmapClient.jmap_url`. A GET request to `/jmap` does not return the session document.

### Local Files

These files are Git-ignored and belong to this workspace. A fresh checkout does not contain the credentials, database, or prepared runtime configuration.

| Path Relative to the Project Root | Purpose |
| --- | --- |
| `dockers/email-system/.env` | Local account credentials, image selection, and ports |
| `dockers/email-system/.data/stalwart/config.toml` | Active configuration mounted at `/etc/stalwart/config.toml` |
| `dockers/email-system/.data/stalwart/server.env` | Selected server environment variables, including the bootstrap credential |
| `dockers/email-system/.data/stalwart/test-agent.json` | Mailbox credential file for Houmao client tests |
| `dockers/email-system/.data/stalwart/data/` | Persistent RocksDB data |
| `dockers/email-system/.data/stalwart/server.log` | Server and runtime output |
| `dockers/email-system/.data/stalwart/runtime.json` | Last recorded launcher PID, container identity, endpoints, and paths |
| `dockers/email-system/.data/stalwart/verification.json` | Last completed live verification result |

The active configuration derives from [the tracked template](dockers/email-system/stalwart/config.toml), with loopback listener bindings and these local additions:

```toml
http.url = "'http://127.0.0.1:10080'"
spam-filter.enable = false
version.spam-filter = "0"
```

The `http.url` expression makes discovered JMAP URLs usable from this workspace. Spam filtering and external spam-rule bootstrap are disabled for this local mailbox fixture. The pinned `v0.15.5` image matches the repository's TOML configuration and management API helpers; changing to newer configuration formats requires a separate update.

### Start or Reuse the Existing Container

The tools, cached image, named container, and local files above are already prepared on this workspace. The following command starts a detached process and refreshes `runtime.json`. It reuses the recorded running instance when present.

```bash
cd /data/huangzhe/code/houmao
pixi run python - <<'PY'
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import socket
import subprocess

root = Path.cwd() / 'dockers/email-system/.data/stalwart'
state = root / 'runtime.json'
metadata = json.loads(state.read_text())
name = metadata['container_name']
pid = metadata.get('pid')
if pid:
    process = Path(f'/proc/{pid}')
    try:
        live = process.joinpath('stat').read_text().rsplit(')', 1)[1].split()[0] not in {'Z', 'X'}
        matches = name.encode() in process.joinpath('cmdline').read_bytes()
    except FileNotFoundError:
        live = matches = False
    if live and matches:
        print(f'{name} is already running; launcher PID {pid}')
        raise SystemExit(0)

for port in (10080, 10143, 10587):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', port))

tools = Path.home() / '.local/share/houmao-email-system'
command = [
    str(tools / 'udocker-venv/bin/udocker'),
    'run', '--nometa', '--nobanner', '--workdir=/opt/stalwart',
    f'--volume={root}:/var/lib/stalwart',
    f'--volume={root / "config.toml"}:/etc/stalwart/config.toml',
    f'--env-file={root / "server.env"}',
    '--entrypoint=/usr/local/bin/stalwart',
    name, '--config', '/etc/stalwart/config.toml',
]
environment = os.environ.copy()
environment['UDOCKER_DIR'] = str(tools / 'udocker')
with (root / 'server.log').open('ab', buffering=0) as output:
    process = subprocess.Popen(
        command, env=environment, stdin=subprocess.DEVNULL,
        stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
    )
metadata['pid'] = process.pid
metadata['restarted_at'] = datetime.now(UTC).isoformat()
state.write_text(json.dumps(metadata, indent=2) + '\n')
print(f'Started {name}; launcher PID {process.pid}')
PY

pixi run python dockers/email-system/provision_stalwart.py \
  --env-file dockers/email-system/.env wait-api --timeout-seconds 45
```

The launcher PID belongs to `udocker`; PRoot and the native `stalwart` process are its descendants. PIDs change across starts. `udocker ps` lists container filesystems, so check HTTP readiness to establish whether the server is running.

### Stop and Restart

Stop the native server gracefully, then wait for its launcher and descendants to exit. This releases the RocksDB lock before another start.

```bash
pixi run python - <<'PY'
import json
import os
from pathlib import Path
import signal
import time

state = Path('dockers/email-system/.data/stalwart/runtime.json')
metadata = json.loads(state.read_text())
pid = metadata.get('pid')
if not pid or not Path(f'/proc/{pid}').exists():
    print('Recorded launcher has already stopped')
    raise SystemExit(0)
if metadata['container_name'].encode() not in Path(f'/proc/{pid}/cmdline').read_bytes():
    raise SystemExit('Recorded PID no longer belongs to this container; inspect before stopping')

owned = set()
pending = [pid]
while pending:
    current = pending.pop()
    directory = Path(f'/proc/{current}')
    if current in owned or not directory.exists():
        continue
    owned.add(current)
    children = directory / 'task' / str(current) / 'children'
    if children.exists():
        pending.extend(map(int, children.read_text().split()))
servers = [p for p in owned if Path(f'/proc/{p}/comm').read_text().strip() == 'stalwart']
if len(servers) != 1:
    raise SystemExit('Expected one owned Stalwart process; inspect before stopping')
os.kill(servers[0], signal.SIGTERM)

def alive(number: int) -> bool:
    """Return whether an owned process is still running."""

    try:
        return Path(f'/proc/{number}/stat').read_text().rsplit(')', 1)[1].split()[0] not in {'Z', 'X'}
    except FileNotFoundError:
        return False

for _ in range(150):
    if not any(alive(p) for p in owned):
        metadata['pid'] = None
        state.write_text(json.dumps(metadata, indent=2) + '\n')
        print('Stalwart stopped; persistent data retained')
        break
    time.sleep(0.1)
else:
    raise SystemExit('Shutdown is still in progress; inspect server.log before restarting')
PY
```

To restart, complete the stop procedure, then run the start procedure. Keep `.env`, `server.env`, and `data/` to preserve credentials and mailbox contents.

### Verify the Running Service

```bash
curl --fail --silent --show-error http://127.0.0.1:10080/healthz/live
curl --fail --silent --show-error http://127.0.0.1:10080/healthz/ready
pixi run python dockers/email-system/provision_stalwart.py \
  --env-file dockers/email-system/.env verify-defaults
```

Run an authenticated SMTP-to-IMAP round trip against the workspace listeners:

```bash
pixi run python - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path('dockers/email-system').resolve()))
from provision_stalwart import load_stack_config
from smoke_mail_flow import send_and_verify_mail

configuration = load_stack_config(Path('dockers/email-system/.env'))
send_and_verify_mail(configuration, '127.0.0.1', timeout_seconds=30)
print('SMTP submission and IMAP delivery passed')
PY
```

The [recorded live verification](dockers/email-system/.data/stalwart/verification.json) also covers mailbox authentication, bounded JMAP queries, metadata-only fetches, explicit body retrieval, `Email/changes`, `Email/queryChanges`, and read-state updates. That report is a snapshot; the commands above check current health and delivery.
