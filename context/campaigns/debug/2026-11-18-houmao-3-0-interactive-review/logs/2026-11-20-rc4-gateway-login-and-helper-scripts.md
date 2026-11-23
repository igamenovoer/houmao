# RC4 Gateway Login and Operator Scripts

Date: 2026-11-20. Status: rc4 interactive gateway login verified; the first admin key was enrolled; the login helper script was generated, its parser was fixed, and the page path-whitespace bug was filed as [#89](https://github.com/igamenovoer/houmao/issues/89).

Context: [debug-intent.md](../debug-intent.md), [MCP install and update log](2026-11-20-dsh-mcp-install-and-update.md).

## Gateway Admin Enrollment

The live gateway at `http://127.0.0.1:36205` started with an empty admin roster, so `admin_access` was `open` and `gateway web-entry` was refused with:

```text
Web entry requires an enrolled admin signer. Set admin_signer_path in the gateway access configuration.
```

A fresh Ed25519 key was generated outside the checkout:

```text
/home/huangzhe/.local/state/houmao-30-iter2-rc4/keys/gateway-admin-ed25519
/home/huangzhe/.local/state/houmao-30-iter2-rc4/keys/gateway-admin-ed25519.pub
```

Both files are owner-only. The private key has no passphrase for automation. Its public fingerprint is:

```text
SHA256:SrjydTXV4zfRDfK9z9AoPOxgnHj012mtH_owV_aVFOo
```

The key was registered as the first admin through `GatewayClient` with a `purpose=register` binding and the owner-local gateway address. The gateway was then detached and reattached with this private access configuration:

```json
{
  "schema_version": 1,
  "bind_host": "127.0.0.1",
  "bind_port": 36205,
  "public_input_enabled": false,
  "advertised_url": null,
  "admin_signer_path": "/home/huangzhe/.local/state/houmao-30-iter2-rc4/keys/gateway-admin-ed25519"
}
```

Stored at `/home/huangzhe/.local/state/houmao-30-iter2-rc4/gateway-access.json`, mode `0600`.

The endpoint now reports `admin_access: key_required`, and `gateway web-entry` issues a one-time URL and expiry. The URL file is private and is not recorded here.

## Interactive Login

The bare interactive page is:

```text
http://127.0.0.1:36205/v1/web/enter
```

The complete flow was exercised with a headless browser:

1. Enter the absolute private key path.
2. Click **Start Login**.
3. Run the generated terminal command.

The terminal returned:

```text
Login approved. Return to the browser.
```

The page then navigated to `http://127.0.0.1:46061/` with title **DeepSeek Harness**. The login mechanism works with the enrolled key and the configured signer.

Two findings:

- The generated login command can contain a malformed path such as `-f './ /home/...'` when the key-path field has leading whitespace. The cause is `src/houmao/gateway/_web_login.js:20`, which tests `keyPath.startsWith("/")` before trimming. The page then prepends `./` to an absolute path. The one-time command was corrected to the absolute path and the login was approved. Filed as #89 with a proposed trim fix and a regression-test gap.
- After login, the DSH sidebar shows `New Session` and `Ungrouped`, but not the managed conversation `session-c22df0f3-5c06-4362-bab0-897fc205c0c0`. The manual says to select the managed conversation in the native sidebar; this build does not list it. That is a separate DSH session-list/UI gap.

## One-Time Link Expiry

A `gateway web-entry` link was issued at 13:53:27 local with expiry 13:54:27. Opening it later produced "Web entry expired or is unavailable." The gateway stayed healthy and the presence id did not change; the one-time link simply has a 60-second window and is consumed on first successful use. The interactive page avoids this race because it creates the ticket after the terminal proof.

## Login Helper Script

The campaign convention now requires both scripts for every agent start, recorded in [debug-intent.md](../debug-intent.md#operator-watch-and-login-scripts):

- `tmp/<iteration-root>/attach-<run-label>.sh`
- `tmp/<iteration-root>/login-<run-label>.sh`

The current login helper is:

```text
tmp/houmao-30-iter2-rc3/login-web.sh
```

Mode `0700`. A run-local copy remains at `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9/login-dsh.sh`.

Behavior:

1. Resolve the run-scoped Houmao roots and agent id.
2. Run `gateway web-entry`, capturing stderr.
3. Parse the indented plain output for `url` and `expires_at_utc`.
4. Write the URL to `web-entry-url.txt` with mode `0600` and the error to `web-entry-url.txt.err`.
5. Open the link with `xdg-open` when available; otherwise print the private file path and expiry.
6. Never echo the one-time URL.

The first script version reported "No URL was issued" even though `web-entry` had succeeded. It anchored the parser at `^url`, while the command output is indented (`  url ...`). The parser now allows leading whitespace (`^[[:space:]]*url[[:space:]]`), and the stderr capture is explicit. This was a campaign-helper bug, separate from the page's #89 whitespace bug.

## Verification State

- Gateway: `healthy`, `connected`, `admin_access: key_required`
- Presence id: `b835727ca5624adca08eae8b56731858`
- DSH native origin: `http://127.0.0.1:46061`
- Native session preserved: `session-c22df0f3-5c06-4362-bab0-897fc205c0c0`
- One-time link file: `tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-web-manager-2752bd4a0bc9/web-entry-url.txt`, mode `0600`; its URL is not recorded here
- `houmao-mgr manual communicate gateway` confirms that `web-entry` requires an enrolled admin signer and that the bare entry URL offers interactive login

## Next Steps

- Fix #89 by trimming the key path before the absolute-path check and adding a regression test for leading and trailing whitespace.
- Investigate why the managed DSH conversation is absent from the native sidebar after login.
- Treat the unencrypted admin private key as a high-value secret; rotate it if the test key is no longer needed.
- Regenerate both scripts after a relaunch because the tmux session, gateway presence, and origin can change.
