# Iteration 3 R11: Kimi Mail Failure Was a Fixture Tmux-Shim False Negative

Date: 2026-11-24. Status: diagnosed; no product or fixture code changed.

## Symptom

In the R11 Kimi Web chat, the operator asked:

```text
tell the other agent to find the latest rsi (self improving) papers using s2 (key in bashrc) and send back the result
```

Kimi correctly routed through `houmao-agent-entrypoint` → `houmao-shared-routines` → `agent-messaging` and chose mail as the transport. It then ran:

```bash
houmao-mgr --print-json agents single \
  --agent-id 3f29cd65-06c0-4b63-8fcf-f8fa13ed556d mail resolve-live
```

and received:

```text
Error: Cannot resolve live managed-agent mail bindings for managed agent `dsh-mailer-r11`.
The shared registry still says this local managed agent is active, but its tmux-backed runtime authority is stale or missing.
```

A follow-up read-only `state` command returned the same error. Kimi then checked the peer session directory and probed `http://127.0.0.1:39909/`, which returned HTTP 401 with `dsh web authentication required; reopen the URL printed by dsh web.` The DSH server was alive. Kimi did not run `stop`, `relaunch`, or `cleanup` because the coordination rules forbid implicit peer recovery; it reported the failure. The turn ended as `cancelled` in the native session state.

## Root Cause

The peer is healthy. The failure is a false negative created by the fixture's private tmux shim.

Each prepared fixture run places a `bin/tmux` shim first on `PATH`. The Kimi run's shim is:

```sh
#!/bin/sh
unset TMUX TMUX_PANE
case "$1" in
  -S) [ "$2" = /tmp/tmux-1001/houmao-fixture-self-hosted-kimi-web-manager-ed9c8416cc2c ] || exit 2 ;;
  -S/tmp/tmux-1001/houmao-fixture-self-hosted-kimi-web-manager-ed9c8416cc2c) shift ;;
  -S*|-L*) exit 2 ;;
esac
case "$1" in -S*|-L*) exit 2 ;; esac
exec /usr/bin/tmux -S /tmp/tmux-1001/houmao-fixture-self-hosted-kimi-web-manager-ed9c8416cc2c "$@"
```

When Kimi's `houmao-mgr` resolves the DSH peer, `_probe_local_tmux_authority_for_record()` calls `tmux_server_scope(record.terminal.socket_path)`, which invokes:

```text
tmux -S /tmp/tmux-1001/houmao-fixture-self-hosted-dsh-web-manager-b6f3732eeb5d ...
```

The Kimi shim sees a `-S` path that is not its own socket and exits `2`. `probe_tmux_backed_authority()` catches the tmux command failure and classifies the peer as `stale_missing_session`, producing the misleading `local_stale` diagnostic.

The DSH agent is alive and reachable:

- Its tmux session exists: `HOUMAO-dsh-mailer-r11-1795489232224` on `/tmp/tmux-1001/houmao-fixture-self-hosted-dsh-web-manager-b6f3732eeb5d`.
- Its web origin `http://127.0.0.1:39909/` returns 401, not a connection refusal.
- Its supervisor and gateway processes are running.
- Its registry record has the correct terminal socket and manifest path.

## Reproduction

With the Kimi shim on `PATH`, the peer resolution fails:

```bash
PATH="$ROOT/runs/self-hosted-kimi-web-manager-ed9c8416cc2c/bin:$PATH" \
  houmao-mgr --print-json agents single \
  --agent-id 3f29cd65-06c0-4b63-8fcf-f8fa13ed556d mail resolve-live
# -> Error: ... tmux-backed runtime authority is stale or missing
```

Without the shim, the same command succeeds and returns the peer's live binding and gateway:

```json
{
  "canonical_mail_identity": {
    "address": "dsh-mailer-r11@houmao.localhost",
    "channel": "offline"
  },
  "gateway": {
    "base_url": "http://127.0.0.1:32995",
    "port": 32995
  }
}
```

## Impact

Any cross-agent operation that probes a peer's tmux authority fails when invoked from inside a fixture run, even though both agents share the same registry and are healthy. This affects `mail resolve-live`, `state`, and likely `inspect` or any path that calls `_probe_local_tmux_authority_for_record()` against another run's socket.

The Kimi agent behaved correctly under the coordination rules: it did read-only checks and refused to recover the peer implicitly.

## Recommended Fix

Filed as [issue #95](https://github.com/igamenovoer/houmao/issues/95): the fixture tmux shim should allow any `houmao-fixture-*` socket while still rejecting the user's default tmux server and unrelated sockets.

Relax the fixture shim to permit explicit `-S` targets under the fixture socket root, while still rejecting the user's default tmux server and unrelated sockets:

```sh
case "$1" in
  -S)
    case "$2" in
      /tmp/tmux-*/houmao-fixture-*) ;;
      *) exit 2 ;;
    esac
    shift 2
    ;;
  -S/tmp/tmux-*/houmao-fixture-*) shift ;;
  -S*|-L*) exit 2 ;;
esac
```

An alternative is to remove the shim from the managed agent's `PATH` and rely on explicit `-S` arguments plus `TMUX`/`TMUX_PANE` clearing, but the narrower allowlist keeps the isolation guarantee against the default server.

After changing the shim, rerun the same `mail resolve-live` from inside the Kimi session and then continue the M1/M2 mail rounds.

## Evidence

- Kimi native session: `session_36bf07ed-e4ea-474c-bab3-594a4cbff298`
- Kimi session record: `.../sessions/wd_workdir_50e24fe9d651/session_36bf07ed-e4ea-474c-bab3-594a4cbff298/state.json`
- Kimi wire log: `.../agents/main/wire.jsonl`
- DSH tmux session: `HOUMAO-dsh-mailer-r11-1795489232224`
- DSH web origin: `http://127.0.0.1:39909/` (HTTP 401, alive)
- DSH gateway: `http://127.0.0.1:32995`
- Kimi shim: `tmp/houmao-30-iter3-mailbox-r11/runs/self-hosted-kimi-web-manager-ed9c8416cc2c/bin/tmux`
