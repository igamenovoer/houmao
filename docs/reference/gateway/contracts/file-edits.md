# Versioned File Edit HTTP Contract

Versioned file edits use the target agent's directly attached gateway. Each operation is a `POST` to `/v1/control/file-edits/<operation>` with a JSON object and an empty query string. Clients select the owner, target generation, and listener from trusted deployment and discovery records. The gateway checks these coordinates again at admission. [Gateway Access and Remote Deployment](../operations/access.md)

Every body includes `target` and `presence_id`. `target.owner` contains `agent_id` and `context_id`, and `target.incarnation` contains the runtime generation. Every operation except `mounts` also requires an exact `mount_id`. Send fresh SSHSIG proof for the exact method, path, and body to identify a registered caller. Unsigned requests use open admission when the admin roster is empty and the configured default group when it is keyed. The gateway sends `Cache-Control: no-store` on successful file responses.

## Operations and Permissions

Permissions are scoped to `files:<mount-id>`. The gateway checks the current permission for an operation and rechecks that authority before revealing protected files and metadata or handing off side effects. Mount discovery returns each qualified mount the caller can read, including its `mount_id`, display `name`, `kind`, policy `resource`, supported `actions`, and `published_commit`. A requested kind that the target cannot expose returns HTTP 501.

| Operation suffix | Permission | Additional request fields |
| --- | --- | --- |
| `mounts` | Filters on `files.read` per mount | Optional `kind` (`skills` or `mcp`) |
| `list` | `files.read` | Optional `revision`, `directory`, `after`, `limit` |
| `read` | `files.read` | `path` and optional `revision` |
| `diff` | `files.read` | `commit_id` and optional `after`, `limit` |
| `history` | `files.read` | Optional `history` (`published` or `candidates`), `after`, `limit` |
| `status` | `files.read` | `operation_id` |
| `lease/open` | `files.edit` | `expected_base` |
| `lease/renew`, `draft/abort` | `files.edit` | `draft_id` and `lease_capability` for anonymous drafts |
| `draft/list` | `files.edit` | Draft selector and optional `directory`, `after`, `limit` |
| `draft/diff` | `files.edit` | Draft selector and optional `after`, `limit` |
| `draft/read`, `draft/mkdir`, `draft/delete` | `files.edit` | Draft selector and `path` |
| `draft/write` | `files.edit` | Draft selector, `path`, and `content_base64` |
| `draft/rename` | `files.edit` | Draft selector, `path`, and `destination` |
| `draft/commit` | `files.edit` | Draft selector and `message` |
| `push` | `files.push` | `commit_id`, `expected_base`, `operation_id`, and optional `when_idle` for current managed-self proof |

`list` uses the current published revision when `revision` is omitted. `read` returns `revision`, `path`, and base64-encoded bytes in `content_base64`. Use the returned `revision` to pin later reads to the same tree. For list, diff, and history, continue with `after` set to the returned `next_after`. A null cursor completes the traversal. File paths are relative to the logical mount. Rename and delete can address directories and their descendants. A single file can hold up to 2 MiB of decoded data.

## Drafts and Immutable Candidates

Open a draft with the observed `published_commit` as `expected_base`. Each mount allows one active editing lease at a time. The lease receipt includes the `draft_id`, `base_commit`, admitted `actor`, and `expires_at` in Unix seconds. A draft selector consists of `draft_id` and, for anonymous drafts, the secret `lease_capability` returned at lease creation. Renew before expiry with `lease/renew`. Keep the anonymous capability private. The gateway binds it to the open epoch or default group revision that admitted the lease. History and status omit the capability.

Signed drafts belong to the original actor kind and principal. A newly enrolled key for the same principal can use that draft with current `files.edit` permission. Effects relying on a retired key or grant are refused. A draft falls outside the native provider's published tree. Aborting it or letting its lease expire discards its staged edits.

Commit validates the complete draft and returns an immutable `commit_id` linked to its `base_commit`, authenticated `author`, and target `committer`. `actor` identifies the actual committing caller. The gateway derives those identities from admitted policy and owner execution. Use `diff` with the returned `commit_id` to inspect changes relative to its parent. The gateway uses Dulwich for Git storage. [Request and Receipt Models](../../../../src/houmao/gateway/file_edits/contracts.py)

## Push Preconditions and Retained Receipts

Submit the candidate's parent as `expected_base`. Both its recorded parent and the mount's current published commit must match that base. The gateway checks the target and projection, reserves owner maintenance, and obtains immediate native admission before changing the live tree. When browser activity or managed work wins admission, the push can report `busy` and leaves the candidate available. A confirmed `conflict` with the published base requires a fresh draft based on the current revision.

Choose and retain an `operation_id` before submitting the first request. The gateway records the publisher, mount, generation, candidate, expected base, and timing mode. An authorized repeat by the same publisher with the same intent returns the retained receipt without replaying publication. After gateway restart, use the current verified listener. Reusing an operation ID with a different publisher, generation, candidate, expected base, or timing mode returns HTTP 409.

With `when_idle: true`, the gateway requires current managed-self proof and keeps the exact saved candidate queued until it can acquire native maintenance. A proven busy refusal before the handoff leaves the intent queued. The original listener, generation, registration and policy must still authorize publication at the handoff. An interrupted attempt uses the retained policy and native evidence to settle its receipt without replaying a committed handoff.

Call `status` with the original operation ID after a lost response. Status requires current `files.read`, including for the original publisher. A caller with only `files.push` can receive the result of its own exact submission or repeat. Use a fresh operation ID for an explicit retry after a confirmed `busy` result. A `pending` or `unknown` result may still resolve under the original ID. The gateway retains the owner reservation while it lacks attributable settlement and readiness evidence.

A successful HTTP response carries a typed receipt, including the `outcome`, `published_commit`, `effective_commit`, `activation`, `native_settled`, and `native_ready` fields. Check the receipt to learn whether it confirms publication, native effectiveness, or both. `published` identifies a complete visible revision. Activation can remain `partial` or `unknown` after publication. HTTP 401 and 403 indicate proof or authorization failures. Invalid input returns HTTP 422, oversized file content can return HTTP 413, and an unavailable owner policy or mount can return HTTP 503. [Route Handlers](../../../../src/houmao/gateway/file_edits/routes.py), [Publication and Recovery](../../../../src/houmao/gateway/file_edits/publication.py)
