# Local Development Services

This file records the services running for Houmao development in this workspace. Run the commands below from the project root, `/data/huangzhe/code/houmao`.

## CCCC Native Pixi Service

CCCC runs directly inside this development container through the isolated [Pixi workspace](tools/cccc/pixi.toml). It does not require Docker, a nested container, or a global Rust installation. The native source build and Web UI were verified on this workspace's Linux ARM64 host.

| Item | Current Deployment |
| --- | --- |
| Product | CCCC 0.4.56 |
| Source checkout | `extern/orphan/cccc`, commit `d12732ebd6dfdbc260a59a286bd5e510d04d4832` |
| Build/runtime environment | `tools/cccc/pixi.toml` and its lockfile |
| Toolchain | Pixi-managed Rust 1.88 and Node.js 24; native Cargo development build |
| Web UI | <http://127.0.0.1:8848> |
| HTTP health | <http://127.0.0.1:8848/api/v1/health> |
| Daemon IPC | Owner-private local Unix-domain socket under the selected `CCCC_HOME` |
| Persistent root | `/home/huangzhe/.local/share/houmao-cccc/` |
| `CCCC_HOME` | `/home/huangzhe/.local/share/houmao-cccc/data/` |
| Native executable | `/home/huangzhe/.local/share/houmao-cccc/target/debug/cccc` |
| Process descriptor | `/home/huangzhe/.local/share/houmao-cccc/runtime.json` |
| Private output log | `/home/huangzhe/.local/share/houmao-cccc/server.log` |
| Lifecycle | Detached user process; start manually after this workspace restarts |

The Web listener binds to loopback inside this container. Forward port `8848` through the editor or SSH to open it from another machine. Native service startup needs no model API key. No Groups, actors, or existing agent-session attachments are created by the helper.

### Install, Build, and Start

For a fresh checkout, clone the source into `extern/orphan/cccc` first. Then run:

```bash
pixi install --manifest-path tools/cccc/pixi.toml
pixi run --manifest-path tools/cccc/pixi.toml build
pixi run --manifest-path tools/cccc/pixi.toml start
pixi run --manifest-path tools/cccc/pixi.toml status
```

The source build uses upstream's `Cargo.lock` and embeds its compiled Web UI. Its first build downloads native, Rust, and frontend dependencies. Build caches and service state stay outside the project; the local source checkout remains Git-ignored.

### Stop, Restart, and Inspect

```bash
pixi run --manifest-path tools/cccc/pixi.toml stop
pixi run --manifest-path tools/cccc/pixi.toml start
pixi run --manifest-path tools/cccc/pixi.toml cccc --version
pixi run --manifest-path tools/cccc/pixi.toml cccc doctor
pixi run --manifest-path tools/cccc/pixi.toml cccc daemon status
pixi run --manifest-path tools/cccc/pixi.toml cccc groups
```

`start` reuses this helper's verified owned process. `stop` checks PID birth identity, command, and selected home before signalling it. Runtime metadata and logs are private local files, not repository artifacts. The developer's `HOME` remains unchanged.

Verification covered the native version, daemon health, CLI access, empty Group listing, all 33 embedded JavaScript/CSS assets, and browser rendering without JavaScript page errors. Repeated start and immediate stop/start were exercised. Formatting, Ruff, and strict typing cover the lifecycle helper.

This minimal environment runs the coordination daemon and Web UI. Optional projected-browser/Web Model actors need additional system browser/display/VNC dependencies and were not qualified. Agent credentials and session integration remain explicit later setup steps. See [the helper README](tools/cccc/README.md) for root/port/build overrides and foreground operation.

## CCCC External Receiver Test Service

The compatible protocol-v1 receiver service runs beside the reference service on loopback port `8849`. It uses the pinned CCCC revision above plus [the ordered chat and deferred-Mail patches](extern/tracked/cccc-receiver/upstream.json). The two services have separate daemon homes and ledgers.

| Item | Current Deployment |
| --- | --- |
| Web UI and HTTP | <http://127.0.0.1:8849> |
| Health | <http://127.0.0.1:8849/api/v1/health> |
| Prepared source | `/home/huangzhe/.local/share/houmao-cccc/source-receiver-mail/` |
| Persistent root | `/home/huangzhe/.local/share/houmao-cccc-receiver/` |
| `CCCC_HOME` | `/home/huangzhe/.local/share/houmao-cccc-receiver/data/` |
| Executable | `/home/huangzhe/.local/share/houmao-cccc-receiver/target/debug/cccc` |
| Private descriptor/log | `runtime.json` and `server.log` under the persistent root |
| Receiver protocol | Version `1`; fixed-Actor bearer RPC under `/api/v1/external-receiver/v1/` |
| Provider extensions | Owner-bound immediate chat and explicit deferred Mail with durable ordered-read receipts |
| Verified executable SHA256 | `1a89d73eb09f06fb463bf38ce3aba078b5ca94dd986ecbe764d4b23d92b4378b` |
| Lifecycle | Detached user process; start manually after workspace restart |

Use these explicit selections for start, status, stop, and CLI access:

```bash
export HOUMAO_CCCC_SOURCE="$HOME/.local/share/houmao-cccc/source-receiver-mail"
export HOUMAO_CCCC_ROOT="$HOME/.local/share/houmao-cccc-receiver"
export HOUMAO_CCCC_PORT=8849
pixi run --manifest-path tools/cccc/pixi.toml start
pixi run --manifest-path tools/cccc/pixi.toml status
pixi run --manifest-path tools/cccc/pixi.toml stop
```

For fresh installation, follow [Prepare the Compatible Receiver Service](tools/cccc/README.md#prepare-the-compatible-receiver-service), including its source preparation and build commands. The service does not create agents, Groups, or grants at startup. [The gateway example](examples/cccc-gateway/README.md) explains explicit Actor provisioning and private credential export.

Chat verification on 2026-11-15 passed 13 native provider tests, actual HTTP authority/lease/retry/history checks, and the installed-wheel two-real-agent chat smoke. That smoke used Claude Code 2.1.323, headless manager fixtures, and the local cloud-api DeepSeek profile (`deepseek-flash`). The peer received ordinary chat and authored a reply with native ancestry. Its agents and owned Group were cleaned up; no model key, Actor token, native agent output, or private credential file is tracked.

The Mail extension's clean prepared source passed 26 native inbox tests, 18 receiver/provider tests, six actual Mail HTTP tests, and six isolated recovery tests. Build metadata verifies the executable against the two-patch source selection. [Deferred Mail setup](docs/reference/gateway/cccc-mail.md) documents explicit reads, receipt recovery, and upgrading an earlier prepared checkout. The separate [Mail acceptance map](docs/reference/gateway/cccc-mail-acceptance.md) records installed-wheel, real Stalwart fault/coexistence, and real-agent evidence; service health alone does not establish those gates.

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

The administrator login is `admin`. The regular test mailbox login is `test-agent`, with addresses `test-agent@example.test` and `test-agent@example.com`. Use `test-agent@example.com` for JMAP sending and live attachment qualification. Passwords were generated locally and are stored in `dockers/email-system/.env`, with file permissions `0600`. Keep credential values out of tracked files, command arguments, and shared logs.

Stalwart 0.15.5 validates a new sending identity against a recognized public suffix and rejects `.test`. On 2026-11-14, separate local fixture administration added the `example.com` domain and the `test-agent@example.com` alias without changing the password or removing the original address. Sending-identity initialization belongs to account setup; Houmao attachment only validates an existing authorized identity and never provisions one. The reserved example.com address routes only inside this local test deployment. A second normal fixture account, `test-agent-peer` (`test-agent-peer@example.com`), supports real recipient delivery and reply qualification. Its private credential is `.data/stalwart/test-agent-peer.json` under this service directory. Normal-account setup initializes authorized sending identities and missing Archive folders separately from Houmao attachment. Stalwart can suppress self-delivery as a duplicate of the sender’s Sent object, so delivery checks use the two fixture accounts.

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
