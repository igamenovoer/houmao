# Online Mail Resolver Fields

Read `mailboxes.online` from `houmao-mgr agents self mail resolve-live`, or the explicitly targeted `agents single` equivalent. The slot contains `revision`, optional `binding`, and safe `availability` information. A configured Stalwart binding contains `agent_id`, `channel=online`, `binding_id`, `address`, and `transport=stalwart`.

The resolver does not expose a password, credential-file path, login secret, or management credential. Gateway and manager execution own provider access. An agent performing ordinary mail work must not open runtime manifests or hunt for provider credentials.

Use the exact `gateway.base_url` when present, otherwise the maintained manager command with `--channel online --expected-binding-id <binding_id>`. A provider outage keeps the configured canonical online identity and produces an operational error. It never selects offline delivery.

Keep references scoped to this account binding. Refreshing credentials for the same account can retain its binding ID with a new revision; replacing the account requires a different binding ID and invalidates old targeting. Preserve opaque references through read, reply, mark, move, and archive.
