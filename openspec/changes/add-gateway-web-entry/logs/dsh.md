# DSH Browser Entry Qualification

Qualified both gateway entry flows on DSH `0.2.2-rc.3`, headless Chromium `156.0.8078.4`, and self-hosted `Qwen/Qwen3.8-27B-FP8`. The test used the checkout manager, a purpose-specific owner-only fixture under the ignored `tmp/` tree, an isolated tmux socket, and a disposable Ed25519 enrollment.

```bash
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py prepare \
  --case self-hosted --client dsh --mode web --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"off":"none","low":"low","medium":"medium","high":"high"}' \
  --dsh-compat '{"supports_developer_role":false}' \
  --executable "$PWD/tmp/dsh/npm-runtime/node_modules/.bin/dsh" --run-root "$run_root"
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py launch \
  --run-dir "$run_dir"
env -u TMUX -u TMUX_PANE pixi run python scripts/agents/test-fixtures/fixture.py prompt \
  --run-dir "$run_dir" --prompt 'Reply exactly DSHENTRYBEFORE. Do not use tools.'
```

The first gateway prompt completed. Registered an admin with `GatewayClient.add_admin_key`, then reattached the gateway at its original owner-local address with that admin's signer selected. The native host and conversation remained in place. The filesystem applied inherited permissions to new scratch files, so the test set the private signer and deployment config to mode `0600` before using them. The Playwright run selected the installed Chromium executable because Bun's resolved Playwright package expected a different cached browser path.

| Check | Result |
| --- | --- |
| Signed command | `houmao-mgr --print-json agents single --agent-id "$agent_id" gateway web-entry` returned exactly `url` and `expires_at_utc`. |
| Signed browser entry | A fresh Chromium profile followed the gateway `302` and DSH `303`, received a native HttpOnly `dsh-auth-*` cookie, and reached the clean native root URL. Repeating the ticket returned `410`. |
| Interactive browser entry | A second fresh profile opened the bare URL. The page showed `no-store` and `no-referrer` and started no attempt until clicked. Entering a literal key path with spaces and a single quote produced a working local OpenSSH and curl command. Terminal output reported only approval. Browser polling continued automatically through the same gateway and DSH redirects to a clean native URL and HttpOnly cookie. Gateway-origin local storage, session storage, and cookies were empty before approval. |
| Conversation identity | Both profiles selected the published native session in the DSH sidebar and displayed the first Qwen turn's `DSHENTRYBEFORE` response. |
| Programmatic coexistence | With the interactive browser open, a signed gateway API prompt completed and the same selected browser conversation displayed its `DSHENTRYAFTER` response. |

The browser driver received the gateway ticket or bare entry URL, clean public native origin and session ID, and the literal local key path for interactive login. It read zero native bootstrap or native connection files and never invoked `fixture.py browser-connection`. The gateway supplied the native sign-in redirect. The native cookie, ticket, SSHSIG, and private signer stayed in the private fixture.

After the additional native listener checks landed, both flows passed again against a fresh fixture and two fresh Chromium profiles. The final run confirmed identity by checking the selected native session row and the actual prompt text, avoiding dependence on model response formatting. It also confirmed the command's expiry display and successful terminal approval with an unusable ambient curl proxy and a local curl configuration that requested proxying and redirect following. The generated command connected to the gateway directly. Both fixtures reported `stopped` after `fixture.py stop`.
