# Offline Mail Resolver Fields

Read `mailboxes.offline` from `houmao-mgr agents self mail resolve-live`, or the explicitly targeted `agents single` equivalent. The slot contains `revision`, optional `binding`, and safe `availability` information. A configured binding contains `agent_id`, `channel=offline`, `binding_id`, `address`, and `transport` (`filesystem` or `registry`).

The registry host owns the filesystem store. A remote member does not need its root, SQLite path, or another host's mailbox directory. Ordinary discovery deliberately omits private backend paths, credentials, and secret-resolution inputs. Use the maintained gateway or manager mail surface for both local and remote offline mail.

Preserve the actor's stable agent ID and selected registry context. Offline address uniqueness applies within that registry; no cluster identifier is needed. A stopped recipient remains registered and can receive mail.

Use `gateway.base_url` exactly when present. Select `offline` explicitly and pin `binding_id` on all operations. A changed binding ends the current operation or round; it does not authorize reopening retained history or routing through online mail. Revision changes can preserve a binding identity, while a new registration receives a new binding ID.
