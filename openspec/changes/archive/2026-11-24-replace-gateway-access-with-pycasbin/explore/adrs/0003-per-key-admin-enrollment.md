# Per-Key Admin Enrollment

A keyed target gives full gateway-admin authority only to SSH keys explicitly enrolled in that target's administrator roster. A second key for the same principal receives the principal's scoped grants. Losing the last enrolled admin key reopens full admin access, including when ordinary keys remain.

## Status

Accepted.

## Consequences

To rotate the last admin key without opening the target, enroll the replacement as an admin before removing the old key. Removing an admin qualification ends that key's roster authority. Revoking the credential also ends its ability to prove the principal.
