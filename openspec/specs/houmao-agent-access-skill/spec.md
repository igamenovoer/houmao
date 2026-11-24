# houmao-agent-access-skill Specification

## Purpose

Guide operators and managed peers through retained gateway policy, SSH key enrollment, and authorized calls to a selected agent.

## Requirements

### Requirement: The Agent Access Routine Preserves Actor and Target Scope
Houmao SHALL expose `agent-access` as the `houmao-agent-access` child of `houmao-shared-routines` for both actor entrypoints. It SHALL provide read-only help and distinguish execution-owner policy changes, live gateway administrator operations, and verified peer operations.

#### Scenario: Managed Agent Requests a Grant
- **WHEN** a caller in the managed-agent frame asks to grant itself access to a peer
- **THEN** the routine explains the target owner's enrollment and grant workflow
- **AND THEN** it preserves the managed-agent frame and avoids attempting owner-local administration

#### Scenario: User Asks Where to Configure a Model Credential
- **WHEN** the task concerns a model-provider login or API credential
- **THEN** the routine hands off to the provider credential workflow without changing gateway policy

### Requirement: Owner Policy Guidance Uses the Retained Target Policy
The routine SHALL teach selection of the target by identity and execution owner, explicit initialization, principal and public-key enrollment, scoped grants and roles, inspection, explanation, revocation, and rotation. It SHALL identify which owner-local operations are available with the gateway detached.

#### Scenario: Owner Grants a Peer Permission to Read a Mount
- **WHEN** the target owner supplies a verified peer public key and an exact mount resource
- **THEN** the routine guides the owner through retaining the principal, enrolling the key, granting `files.read` on `files:<mount-id>`, and checking the grant with `access explain`
- **AND THEN** it distinguishes retained policy from whether the live gateway can verify the mount

### Requirement: Roster Guidance Describes Open and Keyed Modes
The routine SHALL teach that a verified initialized empty roster grants all supported gateway permissions to reachable callers, subject to operation prerequisites. It SHALL describe the first-key and last-key transitions, proof of possession, and the distinction between administrator qualification and credential enrollment.

#### Scenario: Operator Rotates the Only Administrator Key
- **WHEN** the operator intends to keep the gateway in keyed mode during rotation
- **THEN** the routine teaches adding the replacement administrator before removing the old qualification
- **AND THEN** it identifies revocation separately when the old key must lose all ability to prove its principal

### Requirement: Peer Guidance Uses Verified Gateway Coordinates
The routine SHALL teach configuring the source's signer from its owner context, exporting only public identity from verified self, and using scoped `access request` for supported signed JSON requests. It SHALL use trusted target identity, URL, context, generation, presence, and applicable TLS trust without exposing private signing material.

#### Scenario: Managed Peer Calls a Gateway Across Accounts
- **WHEN** a verified managed peer has trusted target coordinates and an enrolled key for the requested effect
- **THEN** the routine uses the configured source signer and selected target gateway independently of the source gateway or tmux topology
- **AND THEN** it reports a stale or unauthorized selection without silently changing the target, credential, or transport
