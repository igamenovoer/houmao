# Stalwart JMAP Client Contract

This reference is for Houmao contributors implementing online mailbox adapters and observers. The supported raw client is `houmao.mailbox.stalwart.StalwartJmapClient`; its result models live in `houmao.mailbox.stalwart_models`.

## Connection and Account Validation

Pass the session-discovery URL, such as `http://127.0.0.1:10080/.well-known/jmap`, separately from the login identity and protected credential file. The client reads the credential once when the connection is created. Replacing its source file does not change an admitted connection. Credential refresh creates another validated connection epoch.

Discovery supplies the method POST URL through `apiUrl`. The client accepts HTTPS, or HTTP on a literal loopback address or `localhost`. Advertised request/upload origins must match the discovery origin or an explicitly allowed origin. Discovery GET redirects may stay within the same authorized origin, under the HTTP client's finite hop cap. Cross-origin redirects and mutation POST redirects fail. Provider errors expose protocol codes or HTTP status, without provider response bodies or raw credential material.

`validate_binding(sender_address=...)` selects an explicitly requested account, a valid primary mail account, or the sole eligible mail account. Ambiguous accounts fail. It validates mail/submission capabilities, writable account posture, inbox access, and an exact authorized sending identity. The login string need not equal the requested address. A supplied identity ID must match that address; the client never chooses the first identity as a fallback.

`ValidatedJmapBinding` returns the pinned account, identity, address, discovery/API URLs, capabilities, mailbox-role map, and finite request limits. No attachment operation invokes management APIs. Provisioning remains a separate explicitly selected administrative operation.

Discovery and role lookup are reused within a connection. The role map has a sixty-second refresh policy; normalization never enumerates mailboxes for individual messages. Required roles fail explicitly when missing. Explicitly denied mailbox permissions fail before mutation.

## Metadata Pages and Filters

Use `query_metadata_page(query=JmapMetadataQuery(...), limit=50, position=0, expected_query_state=None)`. Limits must be 1 through 200 and are further constrained by `maxObjectsInGet`. The exact query combines mailbox membership, `$seen`, `$answered`, archive membership, and `since` before pagination. `since` is an exclusive RFC3339 boundary: only messages received strictly after that timestamp match.

Archive state means archive-mailbox membership, even when a message also belongs to the inbox. Excluded membership uses `NOT inMailbox`. `inMailboxOtherThan` would also match messages with another membership and therefore is unsuitable for this exclusion.

Metadata gets request identifiers, dates, addressing, subject, bounded preview, keywords, complete mailbox memberships, size, and `hasAttachment`. They exclude `attachments`, `bodyValues`, `textBody`, HTML bodies, and MIME structures. Stalwart's `attachments` property itself requires loading message content, so a metadata list uses only the lightweight attachment indicator.

`JmapMetadataPage.messages` contains the returned page. Its size is not an exact inbox count. `has_more`, `complete`, and `next_position` describe bounded continuation; `total_count` remains absent unless explicitly established. The client uses a bounded lookahead or next-position probe to establish exhaustion. A caller-provided method budget can suppress a probe; the result conservatively advertises continuation until another page proves exhaustion.

Continuation callers must supply the earlier `query_state` as `expected_query_state`. State drift, missing queried messages, and inconsistent positions produce `StalwartMethodError(error_type="staleCursor")`. No content get follows a rejected continued page. The shared mailbox layer wraps this provider state with owner, channel, binding, account, and exact filter/sort scope. `query_fingerprint(query)` uses prepared role metadata without HTTP requests and includes the resolved role IDs, fixed descending received-time sort, and `collapseThreads=False`. A budgeted role refresh that changes those filters rejects the old snapshot before querying it.

## Observation APIs and Budgets

| Method | Result and Checkpoint Meaning |
| --- | --- |
| `email_state(timeout_seconds=...)` | Captures `Email/get(ids=[], properties=["id"])` state without enumerating history. Obtain this boundary before the bootstrap query. |
| `get_metadata(email_ids=..., timeout_seconds=...)` | Returns one bounded `JmapMetadataBatch` containing messages, authoritative `not_found`, and its own object state. Missing or extra reconciliation entries fail. |
| `changes(since_state=..., max_changes=100, timeout_seconds=...)` | Returns object-state changes with `old_state`, `new_state`, `has_more_changes`, and created/updated/destroyed IDs. Maximum batch size is 500. |
| `query_changes(query=..., since_query_state=..., max_changes=100, timeout_seconds=...)` | Returns a query-specific delta. It has no `has_more_changes` field and does not advance the email-object checkpoint. |
| `metadata_matches_query(message, query)` | Evaluates cached metadata against full mailbox memberships, flags, and time without issuing HTTP requests. Validate roles before using it. |

`method_call_count` counts attempted JMAP methods, including failures. It counts methods inside an HTTP envelope individually. Page results also report their method count. `max_objects_in_get` and `max_calls_in_request` constrain batching. A metadata-page method budget includes incidental role refreshes and prevents another method once exhausted. Finite timeouts propagate through page discovery, role lookup, query, probe, and metadata retrieval.

Apply and commit every change batch before advancing to that response's `new_state`. An intermediate state remains the next `since_state` while `has_more_changes` is true. A newer state returned by a metadata get does not acknowledge intervening changes. `cannotCalculateChanges`, `tooManyChanges`, unsupported methods, or invalid state remain typed protocol errors for bounded observer recovery.

The local reference source is Stalwart 0.16.26, while the project service uses 0.15.5. The reference `queryChanges` implementation derives its result from bounded object changes without returning an object-change continuation flag. Observers therefore use `Email/changes` and bounded filtered requery for correctness. Query deltas require independently qualified compatible behavior before they become an optimization.

## Selected Content and Mutation Outcomes

`get_content(email_id=..., max_body_value_bytes=1048576)` and explicit peek/read retrieve selected text. Limits must be 1 through 1,048,576 bytes. Provider limits apply per body part; Houmao also limits the aggregate returned text. `content_complete`, `content_limit_bytes`, and `content_limit_reason` expose truncated values, missing parts, encoding problems, unavailable text representations, or aggregate limits. Partial content has no implemented continuation/download route and must be treated as an explicit supported-content limit. The raw HTTP response cap is 8 MiB. Content retrieval alone does not mark read.

Send, reply, mark, move, and archive return metadata rather than fetching message bodies. Send checks positive draft creation and submission acknowledgement. Reply obtains addressing/thread headers from metadata, submits once, then marks its parent read/answered. Archive removes inbox membership and marks read.

`StalwartMethodError` preserves a safe provider error code, method, and optional object ID. Per-object `notCreated` and `notUpdated` failures are explicit. `StalwartMutationError` distinguishes `rejected`, `uncertain`, and `confirmed` outcomes and preserves known email/submission IDs. A confirmed submission followed by a failed inspection or parent update remains confirmed. A transport failure while submitting remains uncertain. Neither outcome triggers an automatic resend.

Wire-level coverage lives in [test_stalwart_jmap.py](../../../../tests/unit/mailbox/test_stalwart_jmap.py). It uses a hermetic loopback HTTP provider and inspects actual discovery/method envelopes. [The normal-account qualification tool](../../../../scripts/qualification/stalwart-mail/README.md) records running-service evidence, release differences, and the actual workload.
