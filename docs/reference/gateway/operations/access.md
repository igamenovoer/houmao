# Gateway Access and Remote Deployment

The gateway applies the same access rules on loopback and all-interface listeners. A new managed launch without an admin seed initializes a valid empty list. **Anyone who can reach a gateway with an empty admin list can invoke admin operations**, including interrupt and raw input. Keep that listener within the intended access boundary while enrolling the first key, or preload one or more admin keys before publishing it.

| Access | Admission | Operations |
| --- | --- | --- |
| Public | Anyone who can reach the listener, subject to operation enablement | Health, endpoint descriptor, challenge issuance, notifications, and public prompts |
| Private | Current managed self or a listed admin with verified proof | Detailed status, usage, memory, routine mail, plugin inventory, and declared private plugin routes |
| Admin | Anonymous admission with an empty list, listed admin proof with a nonempty list | Direct and queued controls, reminders, notifier controls, native inspection and refresh, mailbox binding and operator post, AG-UI, and plugin controls |

First-key registration always requires proof of the proposed key. An invalid or unavailable retained policy prevents protected access. The gateway returns HTTP 401 with `WWW-Authenticate: Houmao-SSHSIG` and an applicable challenge path for missing or invalid proof, HTTP 403 when valid proof lacks authority, and HTTP 503 when required policy is unavailable. A failed proof ends the attempt. Gateway access diagnostics can report the target, operation, outcome, and verified principal or anonymous origin. Service identities such as the mailbox sender or plugin Actor remain bound to their configured owner.

## Provision and Retain Admin Access

Use `houmao-mgr agents launch --gateway-admin-seed "$seed_file" ...` to record initial enrollment in the owner-written manifest. The seed file is owner-private JSON outside the checkout. It contains an `admin_keys` array of objects with `principal` and `public_key` fields. Use a complete OpenSSH public key line for each entry and a distinct public key for each enrollment. An omitted file or `{"admin_keys":[]}` selects the empty initial list.

Each supported launch or join generation gets a new Ed25519 self key pair. Detaching and reattaching the gateway within that generation preserves the same self identity. An ended or replaced generation loses self access. Managed self commands resolve current runtime authority and sign locally. The gateway retains the live admin list across detach, restart, and relaunch of the same owner binding. The launch seed never restores a removed key.

Owner-private gateway access storage lives outside the project checkout. Keep launch and attach input files and signer files outside it too. Processes running under the same UID share that account's filesystem authority. Use separate OS accounts or container isolation when one process must be unable to read or replace another process's access state.

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

The endpoint descriptor at `GET /v1/endpoint` gives the advertised URL, target, live presence, current access requirements, and enabled public operations. Registry metadata can lag membership changes. Live admission always reads retained authority. Detach removes live endpoint publication and preserves the roster. Detach before reattaching with changed deployment settings.

Remote clients verify HTTPS through platform certificate trust or a deployment CA bundle provisioned independently of the endpoint. Clients can also select an exact numeric loopback HTTP URL for a configured encrypted tunnel. Gateway clients refuse redirects and retain the selected URL prefix. If endpoint or target identity changes, explicitly select a new binding. For owner-local admin commands, an optional `admin_signer_path` in the private access configuration selects an absolute private key path. The signer must belong to a current admin when keys are required.

## Enroll or Rotate a Key

This Python example uses a private signer already provisioned outside the checkout and its corresponding public key. Set `GATEWAY_URL` to the selected advertised base URL and `GATEWAY_CA` to the deployment CA bundle when needed. Confirm `GATEWAY_AGENT_ID` and `GATEWAY_CONTEXT_ID` from the owner's deployment record before binding a signer.

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

Use an already listed key to add another with `admin.add_admin_key(other_key)`. After verifying the new signer, use `admin.remove_admin_key(key_id)` from a current admin to revoke the old enrollment. If two callers compete to register the first key, only the first successful commit changes the roster. **Removing the final key immediately reopens admin operations to anyone who can reach the listener.** Restrict reachability first when anonymous control is unintended.

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

Commands sign live private operations inside the CLI. Select the current channel and binding ID from scoped mailbox output. Admin callers can use their own bound signer. Owner-file attachment paths on private mail forms require verified admin proof. See the mailbox facade for channel-specific behavior and the separately authorized manager path when the gateway is detached. [Gateway Mailbox Facade](mailbox-facade.md)
