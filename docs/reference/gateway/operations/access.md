# Gateway Access and Remote Deployment

The gateway applies the same access rules on loopback and all-interface listeners. A new managed launch without an admin seed initializes a valid empty list. **Anyone who can reach a gateway with a valid empty admin list can use its enabled private and admin operations.** This includes memory, mail, interrupt, and raw input. Enroll or seed an admin key before exposing an upgraded gateway whose callers should need proof.

| Access | Admission | Operations |
| --- | --- | --- |
| Public | Anyone who can reach the listener, subject to operation enablement | Dashboard, health, endpoint descriptor, challenge issuance, notifications, and public prompts |
| Private | Anonymous admission with an empty list, current managed self or listed admin proof with a nonempty list | Detailed status, usage, memory, routine mail, plugin inventory, and declared private plugin routes |
| Admin | Anonymous admission with an empty list, listed admin proof with a nonempty list | Direct and queued controls, reminders, notifier controls, native inspection and refresh, mailbox binding and operator post, AG-UI, and plugin controls |
| Web entry | Direct anonymous entry with an empty list, enrolled admin approval with a nonempty list, or a current one-time ticket | Browser handoff to the live managed Web agent |

First-key registration always requires proof of the proposed key. An invalid or unavailable retained policy prevents protected access. The gateway returns HTTP 401 with `WWW-Authenticate: Houmao-SSHSIG` and an applicable challenge path for missing or invalid proof, HTTP 403 when valid proof lacks authority, and HTTP 503 when required policy is unavailable. A failed proof ends the attempt. Gateway access diagnostics can report the target, operation, outcome, and verified principal or anonymous origin. Service identities such as the mailbox sender or plugin Actor remain bound to their configured owner.

## Provision and Retain Admin Access

Use `houmao-mgr agents launch --gateway-admin-seed "$seed_file" ...` to record initial enrollment in the owner-written manifest. The seed file is owner-private JSON outside the checkout or in a purpose-specific subdirectory of its Git-ignored `tmp/` tree. It contains an `admin_keys` array of objects with `principal` and `public_key` fields. Use a complete OpenSSH public key line for each entry and a distinct public key for each enrollment. An omitted file or `{"admin_keys":[]}` selects the empty initial list.

Each supported launch or join generation gets a new Ed25519 self key pair. Detaching and reattaching the gateway within that generation preserves the same self identity. An ended or replaced generation loses self access. Managed self commands resolve current runtime authority and sign locally. The gateway retains the live admin list across detach, restart, and relaunch of the same owner binding. The launch seed never restores a removed key.

Owner-private gateway access storage lives outside the project checkout or in a purpose-specific subdirectory of its Git-ignored `tmp/` tree. Keep launch and attach input files and signer files in approved private storage too. Other checkout directories and nested worktrees remain rejected. Processes running under the same UID share that account's filesystem authority. Use separate OS accounts or container isolation when one process must be unable to read or replace another process's access state.

## Bind, Connect, and Advertise

Select deployment settings in an owner-private JSON file. This example expects an HTTPS reverse proxy to reach port 43123 through the owner's loopback interface.

```json
{
  "schema_version": 1,
  "bind_host": "127.0.0.1",
  "bind_port": 43123,
  "public_input_enabled": true,
  "advertised_url": "https://gateway.example.org/agents/writer"
}
```

```bash
houmao-mgr agents single --agent-name writer gateway attach --access-config "$access_file"
```

- The bind host and port describe the backend listener. The default bind is `127.0.0.1`. Use `0.0.0.0` only with explicit validated settings and a network boundary that protects the backend leg. Omit the port to let the OS assign it on first attach. Later equivalent attaches reuse the resolved port.
- The owner-local connection uses `http://127.0.0.1:<resolved-port>` even if the bind is wildcard. An owner-loopback URL from another execution context belongs to that context.
- The advertised base URL is the client endpoint. Configure the proxy to strip its prefix once, preserve the original `Host`, set `X-Forwarded-Proto: https` on the trusted backend leg, and preserve the method, raw query, and request bytes. Protect that leg with owner loopback or a verified deployment boundary. Publish the per-agent gateway through the proxy and keep global passive administration isolated.

The endpoint descriptor at `GET /v1/endpoint` gives the advertised URL, target, live presence, current access requirements, and enabled public operations. Its `private_proof` value is `none` in open mode, `self_or_admin` in keyed mode, and `unavailable` when required policy cannot be read. Registry metadata provides a locator and can lag membership changes. Live admission reads retained authority. Detach removes live endpoint publication and preserves the roster. Detach before reattaching with changed deployment settings.

Remote clients verify HTTPS through platform certificate trust or a deployment CA bundle provisioned independently of the endpoint. Clients can also select an exact numeric loopback HTTP URL for a configured encrypted tunnel. Gateway clients refuse redirects and retain the selected URL prefix. If endpoint or target identity changes, explicitly select a new binding. For owner-local admin commands, an optional `admin_signer_path` in the private access configuration selects an absolute private key path. The signer must belong to a current admin when keys are required.

## Enroll or Rotate a Key

This Python example uses a private signer already provisioned in approved private storage and its corresponding public key. Set `GATEWAY_URL` to the selected advertised base URL and `GATEWAY_CA` to the deployment CA bundle when needed. Confirm `GATEWAY_AGENT_ID` and `GATEWAY_CONTEXT_ID` from the owner's deployment record before binding a signer.

```python
import os
from pathlib import Path

from houmao.agents.realm_controller.gateway_client import GatewayClient
from houmao.gateway.access import GatewayAdminKey, GatewayClientBinding, GatewayOwner

owner = GatewayOwner(
    agent_id=os.environ["GATEWAY_AGENT_ID"],
    context_id=os.environ["GATEWAY_CONTEXT_ID"],
)
signer_path = os.environ["GATEWAY_SIGNER"]
key = GatewayAdminKey(
    principal="writer-operator",
    public_key=Path(os.environ["GATEWAY_PUBLIC_KEY"]).read_text().strip(),
)
binding = GatewayClientBinding(
    base_url=os.environ["GATEWAY_URL"],
    owner=owner,
    purpose="register",
    private_key_path=signer_path,
    ca_bundle_path=os.environ.get("GATEWAY_CA"),
)
first = GatewayClient(binding=binding, registration_key=key)
key_id = first.add_admin_key(key)
admin = GatewayClient(binding=binding.model_copy(update={"purpose": "admin"}))
status = admin.status()
```

The client requests a challenge from `POST /v1/auth/challenge`, checks the issuer, target, purpose, key, and exact operation, and signs the canonical challenge in the Houmao SSHSIG namespace. The operation carries the challenge ID in `Houmao-Challenge` and the encoded SSHSIG in `Houmao-Signature`. Challenges expire, authorize only the exact method, path, query, and body digest, and can be consumed once. Keep proof in headers and out of URLs and logs. The gateway verifies standard SSHSIG in process.

Use an already listed key to add another with `admin.add_admin_key(other_key)`. After verifying the new signer, use `admin.remove_admin_key(key_id)` from a current admin to revoke the old enrollment. If two callers compete to register the first key, only the first successful commit changes the roster. **Removing the final key immediately reopens enabled private and admin operations to anyone who can reach the listener.** Restrict reachability first when anonymous access is unintended.

## Open a Live Web Agent

On the execution owner, use `houmao-mgr agents single --agent-id "$agent_id" gateway status` to find the live gateway's `gateway_port`. Open the owner-local base URL, for example `http://127.0.0.1:43123/`. The dashboard shows the agent's name or ID, backend, run mode, gateway health, and native Web availability.

Select **Open agent Web UI** when the dashboard offers it. The link opens `/v1/web/enter`. With a valid empty admin roster, the gateway opens the native app immediately. With enrolled keys, it opens the Houmao sign-in page.

For DSH Web, the handoff opens the manifest-bound conversation in the Workspace for its launch workdir. You can navigate to other native conversations. Houmao prompts and mail notifications still target the bound session. Select **Open agent Web UI** again to return to it. [DSH Browser Entry](../../run-phase/dsh-web.md#browser-entry-and-exact-session-selection)

Browser entry works while the native Web agent is busy or waiting for input. The dashboard explains when the action is unavailable, including for agents in other modes or on advertised proxy connections. Use the owner-local address or private TCP forwards for browser entry. The managed agent's `native_surface` publishes the native origin and conversation ID. [Reach Both Owner Addresses](#reach-both-owner-addresses)

### Sign In From the Browser

1. Select **Start Login** on the sign-in page. To use one key, enter an absolute private-key path or a path relative to the terminal's working directory. Write the full home path in place of `~`. The field trims surrounding whitespace and preserves spaces inside the path. An empty result selects supported keys from the terminal's SSH agent.
2. Check the agent and gateway address shown by the page. Select **Copy Command** and run the command in a trusted POSIX-compatible shell with `ssh-keygen` supporting `-Y sign` and `curl`. Blank-path selection also needs `ssh-add`, an active SSH agent, and the standard `mktemp`, `wc`, `rm`, and `rmdir` utilities. OpenSSH signs locally and prompts for any passphrase in the terminal. Curl sends the proof directly to the displayed gateway address.
3. Keep the initiating tab open. It continues to the native app after the terminal approves the login. The login attempt expires after two minutes. To recover after expiry, restart, or refusal, return to the dashboard and select **Open agent Web UI**.

### Issue a One-Time Link

On a gateway with enrolled keys, set `admin_signer_path` to a current enrolled signer in the gateway's private access configuration. With an empty roster the command issues the link unsigned. Run it on the execution owner:

```bash
houmao-mgr --print-json agents single --agent-id "$agent_id" gateway web-entry
```

The command prints `url` and `expires_at_utc`. Open the URL in the browser within 60 seconds to go directly to the native app. Keep the link private and out of shared logs. Anyone who can reach the exact gateway address and holds the unused link can redeem it once.

A signed script can also call `issue_web_entry_ticket()` on a `GatewayClient` with an admin binding for the exact owner-local base URL. Use the bound signer and target from the enrollment example, with the owner-local address in place of the advertised address and direct transport selected:

```python
local_binding = binding.model_copy(
    update={"base_url": "http://127.0.0.1:43123", "purpose": "admin", "ca_bundle_path": None}
)
local_admin = GatewayClient(binding=local_binding, respect_proxy_env=False)
ticket = local_admin.issue_web_entry_ticket()
```

The script receives the same one-time gateway URL. The client refuses HTTP redirects. Give the link to the browser for native authentication.

For a gateway with a valid empty roster, use the unsigned owner-local client:

```python
local_gateway = GatewayClient(base_url="http://127.0.0.1:43123", respect_proxy_env=False)
ticket = local_gateway.issue_web_entry_ticket()
```

```mermaid
sequenceDiagram
    participant B as Browser
    participant G as Owner Gateway
    participant T as Operator Terminal
    participant N as Native Web App
    alt Dashboard entry with an empty roster
        B->>G: Select Open agent Web UI
    else Interactive sign-in with enrolled keys
        B->>G: Select Open agent Web UI and start login
        G-->>B: Challenge and tab claim secret
        T->>G: Sign locally and submit proof with curl
        G-->>T: Approval outcome
        B->>G: Claim the approved login
        G-->>B: One-time URL and expiry
        B->>G: Redeem the ticket
    else One-time link
        T->>G: Request a ticket using the live gateway policy
        G-->>T: One-time URL and expiry
        B->>G: Redeem the ticket
    end
    G->>N: Verify the live Web binding
    G-->>B: Redirect to native sign-in
    B->>N: Authenticate to the native app
    N-->>B: Native conversation
```

DSH exchanges its authentication query for a browser cookie and redirects to a clean page. Select the managed conversation in the native sidebar. Kimi accepts a token fragment and opens the bound conversation. The native app controls the resulting browser session's lifetime. [DSH Web](../../run-phase/dsh-web.md), [Kimi Web](../../run-phase/kimi-web.md)

### Reach Both Owner Addresses

Open Web entry on the execution owner or forward both loopback listeners using private TCP forwarding. Preserve the exact host and port of the owner-local gateway and the published native origin on the browser's machine. The terminal running the generated command must also reach the gateway address shown by the page. For example, if the gateway is `http://127.0.0.1:43123` and the native origin is `http://127.0.0.1:52000`, run this on the browser and terminal machine and keep the connection open:

```bash
ssh -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:43123:127.0.0.1:43123 \
  -L 127.0.0.1:52000:127.0.0.1:52000 \
  owner@example.org
```

For a browser and terminal in separate network namespaces, make the exact gateway address reachable from both. Keep the native forward within the browser's private network boundary. The advertised HTTPS gateway applies the live roster to its API. Exclude Web entry and login routes from its reverse proxy and use the owner-local addresses for browser handoff. [Gateway Protocol and State Contracts](../contracts/protocol-and-state.md#web-entry-and-login)

## Submit an Authenticated Prompt

Use the enrolled admin client from the previous example to submit a ready-only prompt. The client signs the exact request to `POST /v1/control/prompt`.

```python
from houmao.agents.realm_controller.gateway_models import GatewayPromptControlRequestV1

receipt = admin.control_prompt(
    GatewayPromptControlRequestV1(
        prompt="Summarize the current work without changing files.",
        admission_policy="ready_only",
    )
)
```

The receipt reports how far the request reached. A handoff confirms delivery to the native surface. Model completion requires evidence for the same request. After a lost response, inspect the existing operation or the agent's state before sending any new prompt.

## Send Public Input

Public input is disabled by default and has a finite admission budget. The gateway marks input on these two routes as public even when a key holder sends it.

```bash
curl --fail-with-body --cacert "$GATEWAY_CA" "$GATEWAY_URL/v1/messages" \
  --json '{"source_event_id":"mail-421","text":"A review request is available in the offline mailbox."}'
curl --fail-with-body --cacert "$GATEWAY_CA" "$GATEWAY_URL/v1/public/prompt" \
  --json '{"source_event_id":"review-422","prompt":"If policy permits, review the public release notes and mail a brief summary to reviewer@example.org."}'
```

HTTP 200 reports `disposition: dispatched` and the source event ID after confirmed handoff. The response carries no model reply or private result. A caller may ask for a reply by an independent channel, such as mail or an agreed shared file. The agent decides whether policy allows the destination and content. Public payloads cannot select privileged execution controls.

Busy or unavailable work is refused immediately and never queued for later dispatch. HTTP 429 indicates the public budget was exhausted. If confirmation is lost after submission, the caller may receive an uncertain outcome. Retrying can duplicate delivery even with the same source event ID.

## Use Private Mail From a Managed Session

```bash
houmao-mgr agents self mail resolve-live
houmao-mgr agents self mail status
houmao-mgr agents self mail list --channel offline --expected-binding-id "$binding_id"
```

The scoped self commands sign live private operations inside the CLI. Select the current channel and binding ID from scoped mailbox output. Admin callers can use their own bound signer. Owner-file attachment paths on private mail forms use the live admin policy. See the mailbox facade for channel-specific behavior and the separately authorized manager path when the gateway is detached. [Gateway Mailbox Facade](mailbox-facade.md)
