# Change the Default Without a Running Agent

Bob's retained policy controls incoming mail while he is stopped, so his administrator must be able to change the default in that state. Let the administrator write to the same owner policy through a verified direct passive endpoint or an explicit owner-local call.

## Status

Accepted.

## Consequences

Both paths apply the same effective-admin check and policy transaction as the gateway. When Bob's admin changes `agent-requester` to `agent-observer`, subsequent mail admission uses the new revision even while Bob remains stopped. These paths require access to Bob's verified retained policy.
