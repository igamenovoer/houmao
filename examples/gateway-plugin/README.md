# Independent Gateway Plugin Example

This standalone distribution demonstrates the public `houmao.gateway.plugins` SDK. It registers owner inspection, immediate notification dispatch, a supervised heartbeat worker, a successful-dispatch cursor, and optional refresh of a selected private credential document. It does not connect to CCCC or implement a message store.

## Install and Enable

Install the example in the same Python environment that runs `houmao-mgr` and the gateway child. From a Houmao checkout using Pixi:

```bash
pixi run python -m pip install --no-deps ./examples/gateway-plugin
pixi run houmao-mgr agents single --agent-id AGENT_ID gateway attach --plugins-config examples/gateway-plugin/config.example.yaml
```

When `houmao-mgr` belongs to another environment, install the example with that environment's Python. Installing it in the provider CLI's home or in a separate shell environment does not make it available to the gateway child.

For a gateway that already runs with a different selection, detach it first and attach with the new configuration. This restarts only the gateway, leaving the agent body running. An omitted plugin override preserves persisted selections; an explicit empty mapping clears them.

The example advertises `example-notifications` through package entry-point metadata. Configuration creates the instance `team-chat`; the host adds `/v1/plugins/team-chat` to its relative routes.

## Exercise the Routes

Resolve the actual live gateway endpoint through managed-agent gateway discovery. Substitute its base URL below; do not assume the gateway uses a fixed port.

```bash
curl --fail http://127.0.0.1:PORT/v1/plugins
curl --fail http://127.0.0.1:PORT/v1/plugins/team-chat/_status
curl --fail http://127.0.0.1:PORT/v1/plugins/team-chat/owner
curl --fail-with-body -X POST http://127.0.0.1:PORT/v1/plugins/team-chat/notify \
  -H 'Content-Type: application/json' \
  --data '{"source_event_id":"example-001","text":"Read the latest team update.","metadata":{}}'
```

The sender keeps its message until dispatch succeeds. A busy body produces a retryable error; making the body ready later does not deliver the old message. A body that dies or changes during dispatch also causes an error. The sender chooses whether and when to make a new attempt. A lost reply after actual dispatch can make that retry a duplicate.

The example writes only the source ID of a successful dispatch to its contained state directory. It never writes a notification body or a retry spool, and it does not treat the cursor as a durable exactly-once receipt.

## Optional Selected Credentials

For a credential-backed demonstration, create an owner-private JSON file outside the checkout and set its permissions to `0600`. Its `account` field must match the configured account. A real adapter would also validate the authenticated identity against its service.

```yaml
schema_version: 1
gateway:
  plugins:
    team-chat:
      implementation: example-notifications
      credential_ref:
        file: /absolute/private/team-chat.json
      config:
        account: team-chat
        require_credentials: true
```

Keep actual keys outside tracked files and command arguments. After replacing the contents of that selected file, request refresh with an empty object:

```bash
curl --fail-with-body -X POST http://127.0.0.1:PORT/v1/plugins/team-chat/refresh-credentials \
  -H 'Content-Type: application/json' --data '{}'
```

The request cannot select another file or account. Startup and refresh reject a selected document with a different account. The no-auth example never reads ambient credentials.

## Package Boundary

The package imports the public SDK, FastAPI, and Pydantic. It does not import `GatewayServiceRuntime`, inspect queue storage, or depend on a checkout of Houmao. See the [plugin reference](../../docs/reference/gateway/plugins.md) for the complete API and lifecycle contract.

The [installed wheel qualification](qualification.md) records artifact hashes, both normal gateway process modes, immediate failures, gateway/body loss, sender retries, and cleanup using the independent distribution.
