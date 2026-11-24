# Workbench Uses Operator Signers

The single-user AG-UI workbench signs protected Houmao requests with its local operator's enrolled SSH key. Each operator runs a local instance under their own signing configuration. The gateway applies and audits each operator's permissions.

## Status

Accepted.

## Consequences

The workbench backend uses the key only for an authorized local operator session and an explicitly approved target. The browser receives no private key or upstream proof. An operator who can only observe an agent can use its stream, while an operator granted run permission can start work through a separate instance.
