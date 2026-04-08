# Stalwart Transport Guidance

Use this page when the resolved mailbox transport is `stalwart`.

For notifier-driven shared mailbox gateway work, use `houmao-process-emails-via-gateway`.

For shared gateway mailbox actions in ordinary mailbox work, stay on this skill's action pages and use the exact `gateway.base_url` returned by the resolver or already present in prompt or context.

## Stalwart Workflow

- When the current prompt or mailbox context already provides the exact `gateway.base_url`, use that value directly for shared gateway mailbox work and do not rerun manager discovery first.
- Otherwise resolve current mailbox bindings through `houmao-mgr agents mail resolve-live` before mailbox work.
- Treat that resolver output as the manager-owned discovery contract for this turn.
- When the resolver returns a `gateway` object, use this skill's shared `/v1/mail/*` action pages for the ordinary mailbox operation you need.
- When the resolver returns `gateway: null`, use `houmao-mgr agents mail check|send|reply|mark-read` as the supported fallback surface.
- Ordinary mailbox work in this change means `status`, `check`, `send`, `reply`, and marking one processed message read. `post` is explicitly unsupported for `stalwart` in v1.
- Treat `message_ref` and `thread_ref` as opaque shared mailbox references. Do not derive raw Stalwart object identifiers or transport-local structure from the visible prefix.
- After you successfully process one message, mark that same `message_ref` read through `POST /v1/mail/state` when gateway HTTP is in use or `houmao-mgr agents mail mark-read --message-ref ...` when it is not.
- If a fallback `houmao-mgr agents mail ...` result returns `authoritative: false`, treat it as submission-only and verify outcome through `houmao-mgr agents mail check`, `houmao-mgr agents mail status`, or transport-native mailbox state before assuming the mutation completed.

## Stalwart-Specific Guidance

- Read [../references/stalwart-resolver-fields.md](../references/stalwart-resolver-fields.md) before using the transport.
- Use direct Stalwart access only when no live shared gateway mailbox facade is available or when the task falls outside the shared gateway routine surface.
- Use the current `mailbox.stalwart.*` fields returned by the resolver for direct Stalwart-backed mailbox access.
- Treat `mailbox.stalwart.credential_file` as secret material. Read it only when needed for authenticated mailbox access and do not print its contents.
- Use `address` as the sender address for outbound mail.
- Preserve reply ancestry with standard email headers and the opaque `message_ref` contract.

## Guardrails

- Refuse to use this page when `mailbox.transport` is not `stalwart`.
- Do not assume filesystem mailbox `rules/`, mailbox-local SQLite, lock files, or projection symlinks exist for this transport.
- Do not leak raw Stalwart object shapes into operator-facing behavior when a shared mailbox operation can stay transport-neutral.
- Do not present direct env-backed transport access as the first-choice attached-session path when the shared gateway facade is available.
