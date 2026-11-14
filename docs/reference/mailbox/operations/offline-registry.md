# Offline Registry Setup and Remote Access

Each agent can have one offline registration in its selected registry and one independent online account. The registry host owns the offline filesystem store. Remote agents exchange content through the registry API; their runtime directories do not need shared mounts.

An agent keeps its persisted `agent_id` across hosts, sessions, and mail changes. The offline address is unique within the selected registry. There is no cluster identifier. Selecting another registry selects another address namespace; neither offline delivery nor provider mail forwards between namespaces or channels.

## Initialize the Registry Host

Keep service configuration, credential files, mailbox content, and credential-bearing runs outside the checkout. These commands create private local state without printing tokens:

```bash
offline_state="$HOME/.local/state/houmao/offline-registry"
umask 077
mkdir -p "$offline_state"
pixi run python - "$offline_state" <<'PY'
import json
from pathlib import Path
import sys
from houmao.mailbox.registry import prepare_member_credential
from houmao.mailbox.registry_config import OfflineRegistryConfig

root = Path(sys.argv[1]).expanduser().resolve()
prepare_member_credential(root / "admin-token")
config_path = root / "service.json"
if not config_path.exists():
    config_path.write_text(json.dumps({
        "registry_root": str(root / "registry"),
        "mailbox_root": str(root / "mail"),
        "admin_credential_file": str(root / "admin-token"),
        "public_url": "http://127.0.0.1:9892",
        "max_attachment_bytes": 10485760,
    }, indent=2) + "\n")
    config_path.chmod(0o600)
OfflineRegistryConfig.from_file(config_path)
print(config_path)
PY
pixi run houmao-mgr mailbox init \
  --registry-root "$offline_state/registry" \
  --mailbox-root "$offline_state/mail"
pixi run houmao-passive-server offline-registry \
  --config "$offline_state/service.json" --host 127.0.0.1 --port 9892
```

The server runs in the foreground. Use a service manager for automatic startup when needed. Restart it with the same private configuration and store to retain registrations, credential verifiers, and mail. A stopped agent remains registered and can receive messages.

`<registry-root>/offline-mail.json` records the selected mailbox store. Initialization can repeat with the same path. A different project/default mailbox root fails rather than rewriting this association. Maintenance commands can still inspect other roots; membership mutation must select the matching registry, for example with `--registry-root` or `HOUMAO_GLOBAL_REGISTRY_DIR`.

## Connect Another Host

Expose the service through HTTPS termination, or forward a remote loopback listener over SSH:

```bash
ssh -N -L 9892:127.0.0.1:9892 registry-host
```

The client then selects `http://127.0.0.1:9892`. Direct HTTP URLs on non-loopback hosts are rejected. An HTTPS deployment sets `public_url` to its externally protected endpoint. This service has only health, membership, mail, and managed attachment routes; it exposes no body lifecycle, gateway-control, or shutdown APIs.

Enroll and attach an existing locally controlled agent with its persisted ID. The CLI prepares `--credential-file` before enrollment, so a lost response can be retried with the same credential and registration:

```bash
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox offline join \
  --registry-url http://127.0.0.1:9892 \
  --address alice@houmao.localhost \
  --credential-file "$HOME/.local/state/houmao/mail-credentials/alice-token" \
  --admin-credential-file "$HOME/.local/state/houmao/mail-credentials/registry-admin-token"
pixi run houmao-mgr agents single --agent-id "$agent_id" mailbox offline status
pixi run houmao-mgr agents single --agent-id "$agent_id" mail status
pixi run houmao-mgr agents single --agent-id "$agent_id" mail list --channel offline
```

Select an explicit private administrative credential file through your existing secure credential distribution method. Agent IDs and mail addresses are identifiers, not bearer credentials. Credential files and service configuration must be owner-private (`0600`). The service stores only member credential digests in its private index; public discovery contains no credentials or credential-file paths.

Successful attachment preserves the body process, conversation, agent ID, and online slot. It does not require environment refresh or native skill hot reload. If the registry has confirmed membership but local publication failed, repeat the same owner/address/token request and inspect status to reconcile the binding. A different owner claiming an occupied address receives a conflict.

## Administrative Enrollment Through Python

A hub can use the same supported services without launching a body. Administrative enrollment is separate from member-authenticated mail:

```python
from pathlib import Path
from houmao.mailbox.registry import prepare_member_credential
from houmao.mailbox.registry_client import OfflineRegistryClient
from houmao.mailbox.registry_config import read_private_credential

state = Path.home() / ".local/state/houmao/mail-credentials"
member_file = prepare_member_credential(state / "alice-token")
admin = OfflineRegistryClient.from_url(
    "http://127.0.0.1:9892", state / "registry-admin-token"
)
member = admin.enroll(
    agent_id=agent_id,
    address="alice@houmao.localhost",
    member_credential=read_private_credential(member_file),
)
print(member.model_dump_json())  # safe owner/address/registration identity only
client = OfflineRegistryClient.from_url("http://127.0.0.1:9892", member_file)
assert client.self_status().registration_id == member.registration_id
```

`OfflineRegistryClient` defaults to a finite ten-second timeout. It never automatically retries mail mutations or follows redirects with bearer credentials. A network failure can leave a mutation outcome uncertain; inspect authoritative state before repeating a send. Enrollment retries are safe when they reuse the exact prepared owner, address, and token.

Ordinary rejoin does not rotate credentials. An administrator deliberately calls `replace_credential(agent_id, new_token)` after preparing and distributing a new private token. Existing tokens then stop authorizing that member. One active member token cannot identify two different agents.

## Mail and Attachment Contract

Every remote lifecycle operation includes `expected_binding_id`, equal to the selected registration ID. Member release additionally requires `expected_registration_id` on `client.release(...)` or the self-release query, preventing a stale controller from releasing a replacement registration. List results provide owner/channel/binding-scoped message references. Peek, read, reply, mark, move, and archive reject a reference from another owner or a replaced registration before accessing mail. Offline sends use the offline sender address even when the agent's canonical external identity is its online address.

Remote callers upload attachment bytes first. `client.upload(content)` returns a `registry-attachment:<opaque-id>` locator and SHA-256/size metadata. A send supplies that managed locator through its attachment input. Remote adapters upload explicitly selected local files automatically. The registry never opens a path chosen by a remote caller. Downloads require upload ownership or a message projection owned by the current registration, and verify size and digest. The default transfer limit is 10 MiB, configurable in `service.json`.

Read and answered flags do not complete inbox work. Archive is the completion operation. Independent channel notifiers can repeat reminders for unchanged eligible work; an offline registry outage never redirects work through online mail.

## Release and Recovery

`mailbox offline leave` explicitly releases the address. Default deactivation preserves canonical messages and isolates in-root private state under `history/<registration-id>/`. Symlink-backed release removes the registry routing entry while preserving its external target. A new owner receives a fresh registration and empty mailbox view. Neither force/stash modes nor `--yes` permit address takeover.

A failed mailbox preparation leaves a durable `preparing` reservation. The same owner can retry to complete it; another owner cannot take it. OS-owned locks release when a worker exits. A registry service restart preserves ownership independently of runtime leases and tmux probes.

Repair rebuilds derived message indexes while retaining readable ownership and private membership data. Missing, unreadable, or unsupported ownership state requires an operator backup restore or explicit rebootstrap. Mailbox files and message headers cannot establish replacement agent identity or credentials. See [Registration Lifecycle](registration-lifecycle.md) and [Repair and Recovery](repair-recovery.md).

## Verified Behavior

[Process integration tests](../../../../tests/integration/mailbox/test_offline_registry_process.py) start the supported server with an isolated registry host and disjoint agent roots. They cover stopped recipients, response-loss enrollment retry, restart, read/reply/archive, content transfer, address reassignment, concurrent claims, and killed preparation recovery. [Unit tests](../../../../tests/unit/mailbox/test_offline_registry.py) cover route exclusion, authorization, credential rotation, bounded attachment access, history isolation, and store association.
