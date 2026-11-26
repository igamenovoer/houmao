# Attach CCCC to a Running Agent

This example connects one existing Houmao agent to an explicitly provisioned external CCCC Actor. Repeat it with a different Actor, grant, and owner for each peer. The plugin does not launch or control the agent body.

1. Prepare and start the compatible native service using [the native tooling](../../tools/cccc/README.md#prepare-the-compatible-receiver-service). Install the independently built `houmao-cccc` wheel in the gateway's Python environment.
2. Create a Group and an inactive Actor using CCCC's operator interface. Select its actual Group and Actor identifiers. Grant issuance explicitly converts that Actor to external control; it must not be a running native Actor.
3. Export an owner-bound private grant outside the checkout. These arguments contain public identifiers only:

   ```bash
   pixi run python tools/cccc/provision.py \
     --endpoint http://127.0.0.1:8849 \
     --group-id GROUP_ID --actor-id ACTOR_ID --agent-id HOUMAO_AGENT_UUID \
     --output "$HOME/.local/state/houmao/credentials/cccc-actor.json"
   ```

4. Copy [plugins.yaml](plugins.yaml) to a local configuration file. Replace the credential path and public Group, Actor, and generation descriptors using the grant export's output. Do not copy the token into the configuration.
5. Attach the plugin to the existing owner. For a changed live selection, detach the gateway first. The body can keep its current session:

   ```bash
   houmao-mgr agents single --agent-id HOUMAO_AGENT_UUID gateway detach
   houmao-mgr agents single --agent-id HOUMAO_AGENT_UUID gateway attach \
     --background --plugins-config /absolute/path/plugins.yaml
   ```

6. Read `binding` and wait for `connection` to become `connected`. The CLI requires an explicit loopback gateway URL:

   ```bash
   houmao-cccc --gateway-url http://127.0.0.1:GATEWAY_PORT binding
   houmao-cccc --gateway-url http://127.0.0.1:GATEWAY_PORT capabilities
   ```

Give the agent [the usage instructions](agent-instructions.md), substituting its gateway URL, instance, and returned binding ID. A body needs only the local gateway CLI/HTTP interface. Keep the provider grant private to the gateway.

See [the integration reference](../../docs/reference/gateway/cccc.md) for message commands, error handling, reconnects, explicit retries, and cleanup. Revoke only the grants you provisioned and delete only Groups owned by your test.

Version 0.3 supports [explicit deferred Mail](../../docs/reference/gateway/cccc-mail.md) through the same Actor binding through receiver protocol v2. The [chat qualification](qualification.md) and [Mail qualification](mail-qualification.md) record separate installed-wheel and real-agent evidence.
