# Kimi Web Entry Qualification

The managed fixture used Kimi Code `2.6.0`, self-hosted `Qwen/Qwen3.8-27B-FP8`, OpenSSH `9.6p1`, and Playwright Chromium `156.0.8078.4`. The fixture launched in Web mode through the manager with an isolated tmux socket and an owner-only run directory. A managed turn completed before either browser entered.

```bash
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client kimi --mode web --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --executable "$kimi_executable" --run-root "$run_root"
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py launch \
  --run-dir "$run_dir" --prompt 'Reply exactly KIMI_GATEWAY_WEB_QUALIFIED. Do not use tools.'
```

| Check | Result |
| --- | --- |
| Stock native deep link | A fresh browser opened `/sessions/<id>` using the native token fragment, reached the expected managed transcript, received HTTP 200 from the session API, and showed the exact session path with a clean query and fragment. |
| Interactive login over private forwarding | A separate fresh browser visited the bare entry URL and started a login with an empty key path. The browser harness used the published gateway address and native surface. |
| Blank-path OpenSSH agent selection | The isolated SSH agent contained an unenrolled key first and the enrolled admin key second. The generated `ssh-keygen -Y sign -U` and curl command returned the fixed approval message with ambient proxy variables set to an unreachable address. |
| Automatic continuation | The browser claimed the result with HTTP 200 and redeemed the normal ticket with HTTP 302. Kimi authenticated the native session API, opened the bound transcript, and cleared the fragment. |
| Advertised HTTPS | The same gateway's CA-verified signed status succeeded before and after browser entry through an HTTPS prefix proxy. A request to Web entry through that proxy returned HTTP 403. |

The kernel refused an isolated network namespace, which prevented a second set of loopback binds in this environment. A private OpenSSH SOCKS5 tunnel forwarded Chromium's TCP connections to the exact gateway and native loopback addresses. The SSH server allowed only those two destinations. The generated terminal command ran on the owner-local gateway address. The documented static `ssh -L` command was not run in a second network namespace.

The focused native backend, client, model, gateway, and URL-builder unit run passed 99 tests and reported the existing Starlette test-client deprecation warning. Ruff and strict mypy passed on the changed native modules.

The fixture reported `stopped_owned_identity` after cleanup. The private SSH client and listener were stopped.
