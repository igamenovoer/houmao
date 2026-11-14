# Attach Normal Online Mail to a Managed Test Agent

Use this routine only for an explicitly selected development mail test. It attaches an existing normal account; account/domain provisioning remains a separate administrative workflow. No Stalwart management credential belongs in attachment input.

## Workflow

1. Prepare the model/client fixture using `configure-fixtures`, then select the managed launch lane through `launch-fixture`. Keep `self-hosted` and `cloud-api` (DeepSeek) cases generic and explicit. A model API key is independent of the mailbox password. Never substitute ambient model or mail authentication.
2. Capture the launched agent ID, owning runtime/registry/overlay roots, body PID, and conversation marker. Use the roots recorded by the fixture helper for all direct manager commands. Verify its gateway is active through the supported gateway status surface. If it is absent, use the explicit companion-attach workflow for this test-owned agent; do not restart the body merely to add mail.
3. Select the existing normal-account login, authorized sending address, discovery URL, and private credential file. Login and address may differ. Discovery is normally `/.well-known/jmap`; the returned session selects the method API URL. Ambiguous accounts require an explicit account ID.
4. Run online status and retain its slot revision. Attach with that expected revision and the selected private source path. Another bound account requires explicit `--replace`; a conflict is not permission to replace it.
5. Verify the same body PID/conversation and agent ID, preserved offline binding, online account availability, and online-first canonical identity. Enabling a notifier is a separate explicit test step after attachment.
6. Exercise one finite metadata page, selected peek/read, and only the test-authorized mutations. Stop on stale binding/cursor, rejected credentials, endpoint failure, or uncertain send/reply outcome. Never replay uncertain mutations automatically.
7. Test requested refresh/reconnect/restart/detach behavior and hand off sanitized counts plus private evidence locations. Detach only this test's online binding and stop only the fixture-owned runtime when cleanup is requested or the test ends.

## Private Inputs and Supported Commands

The selected credential source is an owner-private JSON file containing a nonempty `password` value. Keep it and credential-bearing runs outside the checkout. Have the developer populate it locally or use an explicitly selected private secret source. Do not place the password in a shell argument, tracked example, report, tmux command, or chat. The CLI accepts `--credential-source FILE`; the corresponding typed request field is `credential_source_ref`.

Run these from the managed Pixi environment with the exact fixture roots already selected. Fill placeholders from the captured fixture and safe status response:

```bash
pixi run houmao-mgr agents single --agent-id '<captured agent id>' gateway status
pixi run houmao-mgr agents single --agent-id '<captured agent id>' mailbox online status
pixi run houmao-mgr agents single --agent-id '<captured agent id>' mailbox online attach \
  --provider stalwart \
  --base-url 'http://127.0.0.1:10080' \
  --login-identity '<selected normal-account login>' \
  --address '<authorized sending address>' \
  --credential-source /external/private/mail-account.json \
  --expected-revision '<observed online slot revision>'
pixi run houmao-mgr agents single --agent-id '<captured agent id>' mail status
pixi run houmao-mgr agents single --agent-id '<captured agent id>' mail list \
  --channel online --expected-binding-id '<selected binding id>' --limit 50
```

Use the exact `--jmap-url` instead of `--base-url` when discovery is at a nonstandard path. The example endpoint is the project-local service, not a required host or port for another checkout. See [SERVICES.md](../../../../SERVICES.md) and the selected deployment. Explicit source/account/URL inputs must identify that deployment; do not use management credentials as a normal-account fallback.

`mail list` has a default of 50 and a maximum of 200, accepts opaque `--cursor`, and returns one metadata page. Preserve channel, binding, and filters across continuation within the test's page/message budget. `has_more` is not an exact mailbox total. Removed `--include-body` fails; use `mail peek` or `mail read`, checking `content_complete` and reported limits before treating content as complete.

For source-file rotation, select the updated source and use `mailbox online refresh` with the current expected revision; it must remain the same account. `reconnect` retains the account/checkpoint and `detach` removes only online binding authority. Do not remove the developer's external source or provider messages as cleanup. Read [the online lifecycle reference](../../../../docs/reference/cli/agents-mailbox.md) for the current control flags rather than inventing them.

## Evidence

Record the actual service release, selected fixture case/client/model, stable body/conversation evidence, safe binding/revision transitions, metadata page/count/completeness, and mutation outcomes. For readonly traffic measurements or the larger workload plan, use [Stalwart qualification](../../../../docs/reference/mailbox/operations/stalwart-qualification.md). A small live test does not establish 100-agent or million-message capacity. Mark unavailable reminder, transfer, or usage measurements as unavailable.
