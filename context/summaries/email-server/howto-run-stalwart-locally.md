# How to Run Stalwart Locally Without Docker

This guide shows how to download, configure, start, verify, and stop a local Stalwart server without Docker and without `sudo`. It is aimed at development and experimentation, especially when you want AI agents or local test clients to talk to a real mail server on localhost.

## Goal

By the end, you will have a Stalwart instance running from a workspace-local directory under `tmp/`, with all listeners bound to `127.0.0.1` on non-privileged ports.

Example ports used in this guide:

- HTTP admin: `127.0.0.1:18080`
- SMTP: `127.0.0.1:2525`
- Submission: `127.0.0.1:2587`
- IMAP: `127.0.0.1:2143`
- POP3: `127.0.0.1:2110`
- Sieve: `127.0.0.1:4190`

## Why This Setup

This layout is convenient for local development because:

- it does not require Docker
- it does not require root privileges
- it keeps all state under `tmp/`
- it avoids port conflicts with system mail services
- it exposes a web admin UI and standard mail protocols for testing

## Directory Layout

In this repository, use a dedicated working directory such as:

```text
tmp/stalwart-nonroot/
```

Expected contents after setup:

```text
tmp/stalwart-nonroot/
  bin/
  data/
  etc/
  logs/
```

## 1. Create the Working Directory

Run:

```bash
mkdir -p tmp/stalwart-nonroot/bin tmp/stalwart-nonroot/etc tmp/stalwart-nonroot/logs tmp/stalwart-nonroot/data
```

If you are working in this repo, the canonical absolute path is:

```text
/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/tmp/stalwart-nonroot
```

## 2. Discover the Latest Release

To avoid hardcoding a version, query GitHub for the latest release:

```bash
curl -fsSL https://api.github.com/repos/stalwartlabs/stalwart/releases/latest | rg '"tag_name"|browser_download_url'
```

For Linux x86_64, look for an asset like:

```text
stalwart-x86_64-unknown-linux-gnu.tar.gz
```

## 3. Download and Extract the Binary

Example using `v0.15.5`:

```bash
curl -fL https://github.com/stalwartlabs/stalwart/releases/download/v0.15.5/stalwart-x86_64-unknown-linux-gnu.tar.gz -o tmp/stalwart-nonroot/stalwart.tar.gz
tar -xzf tmp/stalwart-nonroot/stalwart.tar.gz -C tmp/stalwart-nonroot/bin
chmod +x tmp/stalwart-nonroot/bin/stalwart
```

Verify the binary:

```bash
/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/tmp/stalwart-nonroot/bin/stalwart --help
```

Note: in this workspace, using the real `/data/ssd1/...` path worked more reliably than invoking the binary through the `/data1/...` symlinked working directory path.

## 4. Initialize a Fresh Stalwart Home

Let Stalwart generate a baseline config and admin password:

```bash
/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/tmp/stalwart-nonroot/bin/stalwart --init /data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/tmp/stalwart-nonroot
```

This writes:

- `tmp/stalwart-nonroot/etc/config.toml`
- an admin user named `admin`
- a generated admin password printed to the terminal

Save that password somewhere safe if you plan to use the web admin UI.

## 5. Rewrite the Listeners to Use Localhost High Ports

Edit `tmp/stalwart-nonroot/etc/config.toml` and replace the default low ports with localhost-only high ports.

Recommended minimal config:

```toml
[server.listener.smtp]
bind = "127.0.0.1:2525"
protocol = "smtp"

[server.listener.submission]
bind = "127.0.0.1:2587"
protocol = "smtp"

[server.listener.imap]
bind = "127.0.0.1:2143"
protocol = "imap"

[server.listener.pop3]
bind = "127.0.0.1:2110"
protocol = "pop3"

[server.listener.sieve]
bind = "127.0.0.1:4190"
protocol = "managesieve"

[server.listener.http]
protocol = "http"
bind = "127.0.0.1:18080"
```

For a simple local start, it is reasonable to remove or comment out:

- implicit TLS listeners such as `submissions`, `imaptls`, and `pop3s`
- the HTTPS listener on port `443`

This keeps the first boot focused on plain local connectivity and avoids certificate-related setup.

## 6. Start the Server

Run:

```bash
/data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/tmp/stalwart-nonroot/bin/stalwart --config /data/ssd1/huangzhe/code/agent-system-dissect/extern/tracked/gig-agents/tmp/stalwart-nonroot/etc/config.toml
```

If you want it to keep running while you continue working in the same shell, launch it in another terminal, a tmux pane, or a background job that you manage yourself.

## 7. Verify That It Started

Check listening ports:

```bash
ss -ltnp | rg '127.0.0.1:(18080|2525|2587|2143|2110|4190)'
```

Check the web admin:

```bash
curl -i http://127.0.0.1:18080/login
```

You should see an `HTTP/1.1 200 OK` response and HTML for the Stalwart management UI.

Check logs:

```bash
tail -n 80 tmp/stalwart-nonroot/logs/stalwart.log.*
```

Healthy startup logs usually include lines like:

- `Starting Stalwart Server`
- `Network listener started`
- `Housekeeper process started`

## 8. Sign In to the Web Admin

Open:

```text
http://127.0.0.1:18080/login
```

Use:

- username: `admin`
- password: the one printed by `--init`

From there you can create domains, accounts, aliases, and inspect server settings.

## 9. Stop the Server

Find the PID:

```bash
ps -ef | rg 'stalwart --config'
```

Stop it:

```bash
kill <PID>
```

## 10. What This Gives You for Agent Experiments

With this setup, your project can already:

- send mail to the local SMTP listener on `127.0.0.1:2525`
- retrieve mail via IMAP on `127.0.0.1:2143`
- automate administration through the Stalwart web and management surfaces after initial setup
- keep all runtime data inside the repo-local `tmp/` area

For agent-to-agent messaging, this is a good local integration target because it combines standard mail protocols with a modern Stalwart administration environment, while staying easy to tear down and recreate.

## Next Steps

After basic startup, the next useful tasks are:

1. Create a test domain such as `local.test`.
2. Create one or more mailbox users for your agents.
3. Send a message through SMTP to confirm local delivery.
4. Fetch that message through IMAP from an automated client.
5. Add TLS, authentication policies, and any persistence or backup choices you need for longer-lived environments.

## References

- Stalwart installation docs: <https://stalw.art/docs/category/installation/>
- Stalwart latest release: <https://github.com/stalwartlabs/stalwart/releases/latest>
