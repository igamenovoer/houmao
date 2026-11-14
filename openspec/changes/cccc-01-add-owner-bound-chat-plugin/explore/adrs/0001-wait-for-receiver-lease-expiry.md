# Wait for Receiver Lease Expiry After a Gateway Crash

A replacement gateway waits for the existing CCCC receiver lease to expire after a crash; with the proposed default, the delay can be up to the remaining 45 seconds. Ordinary Actor credentials cannot force replacement, while an explicit CCCC operator action may fence the old generation and permit early takeover. This accepted decision keeps receiver ownership simple without a private lease-resumption mechanism; changing intake authority never retries an unsettled message or grants control of the agent body.

## Considered Options

- Automatic takeover with ordinary Actor credentials offers faster recovery but lets another credential holder displace a live receiver.
- A private lease-resumption secret offers faster same-owner recovery but introduces additional protected state and protocol behavior.

See the [receiver protocol design](../../design.md#4-add-an-authenticated-external-receiver-protocol-to-cccc) and [normative lease scenarios](../../specs/cccc-external-receiver/spec.md).
