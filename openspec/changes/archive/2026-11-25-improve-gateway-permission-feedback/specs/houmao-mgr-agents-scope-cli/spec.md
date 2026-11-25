# Spec Delta

## ADDED Requirements

### Requirement: Owner Access Feedback Explains the Recorded Grant

Successful `agents single access grant` and `revoke` commands SHALL describe the direct grant change and its admission implications at the committed policy revision. Feedback SHALL use stderr and preserve the existing stdout result and exit behavior. Owner inspection SHALL continue to distinguish direct grants from effective decisions.

#### Scenario: A grant changes on an open roster

- **WHEN** the verified owner adds, updates, or revokes a direct grant and the committed snapshot has an open roster
- **THEN** the command reports the recorded grant change and explains that open admission still supplies authority for supported operations at that policy revision
- **AND THEN** the existing JSON result reports the committed revision and mode

#### Scenario: A grant changes on a keyed roster

- **WHEN** the verified owner changes a direct grant and the committed snapshot has a keyed roster
- **THEN** the command directs the owner to `access explain` for the selected principal, resource, and action
- **AND THEN** the feedback makes no allow or deny claim based solely on the direct grant change

### Requirement: Open Policy Initialization Points to First-Admin Enrollment

When `agents single access init` reports a valid open roster, it SHALL use stderr to identify the existing `access admin-add --first` workflow and its verified attached gateway prerequisite. Initialization SHALL keep its existing result and exit behavior.

#### Scenario: An existing open roster is inspected during initialization

- **WHEN** the owner runs `access init` and the existing policy is already initialized with an open roster
- **THEN** the command reports the retained policy and gives first-admin enrollment guidance
- **AND THEN** it creates no key and makes no roster change

#### Scenario: A detached target initializes an open policy

- **WHEN** the verified owner initializes an empty roster without a live gateway
- **THEN** initialization succeeds under its existing contract
- **AND THEN** the enrollment guidance explains that an attached gateway is needed for the suggested command

### Requirement: Selected File Commands Explain Missing Signer Selection

When a keyed endpoint is verified and a selected-agent file command lacks an explicit signer or unsigned selection, the CLI SHALL name the roster mode and show where to supply `--signer`. The CLI SHALL preserve the operator's explicit caller selection and the existing behavior for open or unavailable policy.

#### Scenario: A keyed mount read or push has no caller selection

- **WHEN** `agents single ... files` selects a verified keyed endpoint for `mounts`, `read`, or `push` without a signer or `--unsigned`
- **THEN** the command fails with guidance showing `files --signer <key>` before the file subcommand
- **AND THEN** it points the verified local owner to `access list` for enrollment details
- **AND THEN** it sends no file request and reveals no roster contents or private key path

#### Scenario: The operator explicitly chooses an identity or unsigned admission

- **WHEN** the file command selects a signer or `--unsigned`
- **THEN** the command uses that selection and the existing gateway decision
- **AND THEN** any refusal terminates the attempt without selecting another credential or retrying unsigned

### Requirement: File Authorization Refusals Identify the Attempted Effect

File command diagnostics SHALL retain the HTTP status and report any recognized reason from the existing gateway access error. Diagnostics SHALL identify the requested action, resource, and caller selection where known. They SHALL distinguish selected caller evidence from verified attribution and exclude private input.

#### Scenario: A keyed peer push is denied

- **WHEN** the selected gateway refuses the peer's push with HTTP 403 and `insufficient_authority`
- **THEN** stderr identifies the HTTP status, reason, requested `files.push`, exact `files:<mount-id>`, and caller selection
- **AND THEN** it suggests that the target owner use `access explain` to inspect the decision
- **AND THEN** the command retains its existing nonzero exit and sends no retry

#### Scenario: An access error has limited evidence

- **WHEN** the response is missing a recognized reason or has an invalid error payload
- **THEN** the diagnostic retains the HTTP status and safe request context
- **AND THEN** it prints neither the response body nor an inferred reason or principal

### Requirement: Busy File Push Feedback Explains Explicit Recovery

On a confirmed busy push receipt, the CLI SHALL explain on stderr that the candidate remains saved and a new attempt needs a fresh operation ID. It SHALL suggest `--when-idle` only for the verified owning managed runtime. Existing receipt fields and exit behavior SHALL determine the machine-readable result.

#### Scenario: Managed self immediately pushes during a turn

- **WHEN** a signed `agents self files push` returns a busy receipt attributed to managed self
- **THEN** stderr suggests an explicit `--when-idle` attempt using the saved candidate, recorded base, and a fresh operation ID
- **AND THEN** stdout retains the busy receipt and the command exits nonzero without queuing work

#### Scenario: A peer, owner, or unsigned caller receives busy

- **WHEN** a busy receipt comes from a selected-agent command or an unsigned self command
- **THEN** stderr advises an explicit new attempt once the target is ready
- **AND THEN** the guidance does not offer managed-self scheduling

#### Scenario: A push returns a queued or unconfirmed result

- **WHEN** the service confirms a queued intent or the CLI cannot confirm an attempt
- **THEN** the CLI preserves the existing outcome and operation ID
- **AND THEN** it does not present that outcome as busy or suggest retrying it as a new busy attempt

### Requirement: Selected Agent State Shows Verified Owner Policy in Human Output

Human-readable `agents single state` SHALL show the retained roster mode and default permission group and version when the CLI can verify the selected local owner policy. The added view SHALL preserve the structured state response and keep roster membership, signer labels, fingerprints, and key paths out of state.

#### Scenario: The owner inspects a local agent with a detached gateway

- **WHEN** plain or fancy state output renders a selected local agent with an available current owner policy
- **THEN** it reports the retained mode and group without requiring a live gateway

#### Scenario: A caller lacks current local owner evidence

- **WHEN** a human-readable state command resolves a remote or delegated target, or cannot verify the selected local policy
- **THEN** it renders the normal state with no inferred policy values
- **AND THEN** unavailable policy evidence does not prevent delivery of otherwise available operational state

#### Scenario: A caller requests machine-readable state

- **WHEN** the state command runs with `--print-json` or produces a collected structured result
- **THEN** it produces the existing structured state shape without a new owner-policy lookup
