## MODIFIED Requirements

### Requirement: `houmao-mgr agents gateway` exposes gateway lifecycle and gateway-mediated request commands
`houmao-mgr` SHALL expose a native `agents gateway ...` command family for managed-agent gateway operations.

At minimum, that family SHALL include:

- `attach`
- `detach`
- `status`
- `prompt`
- `interrupt`
- `send-keys`
- `mail-notifier status`
- `mail-notifier enable`
- `mail-notifier disable`

`agents gateway prompt` SHALL target the managed agent's live gateway direct prompt-control path rather than the transport-neutral managed-agent request path or the queued gateway request path.
`agents gateway interrupt` SHALL continue targeting the managed agent's live gateway-mediated interrupt path.
`agents gateway send-keys` SHALL target the managed agent's dedicated live gateway raw control-input path rather than the queued gateway request path, and it SHALL NOT apply prompt-readiness or busy gating before forwarding that raw input.
`agents gateway mail-notifier ...` SHALL target the managed agent's live gateway mail-notifier control path rather than the foreground managed-agent mail follow-up path.
The documented default prompt path for ordinary pair-native prompt submission SHALL remain `houmao-mgr agents prompt ...`. `agents gateway prompt` SHALL be documented as the explicit live gateway prompt-control path for operators who want ready-or-refuse behavior and optional `--force` override semantics.

#### Scenario: Operator attaches a gateway through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway attach --agent-id abc123`
- **THEN** `houmao-mgr` resolves that managed agent through the supported authority for that target
- **AND THEN** the command attaches or reuses the live gateway for that managed agent

#### Scenario: Operator submits a gateway-controlled prompt through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..."`
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway direct prompt-control path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Operator submits raw control input through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway send-keys --agent-id abc123 --sequence "/model<[Enter]>"`
- **THEN** `houmao-mgr` delivers that request through the managed agent's dedicated live gateway raw control-input path
- **AND THEN** the command does not reinterpret that raw control input as a queued semantic prompt request

#### Scenario: Operator enables mail notifier through the native `agents gateway` tree
- **WHEN** an operator runs `houmao-mgr agents gateway mail-notifier enable --agent-id abc123 --interval-seconds 60`
- **THEN** `houmao-mgr` delivers that request through the managed agent's live gateway mail-notifier control path
- **AND THEN** the command does not require the operator to discover or address the gateway listener endpoint directly

#### Scenario: Ordinary prompt guidance points operators to the transport-neutral path by default
- **WHEN** repo-owned help text or docs explain how to submit an ordinary prompt through the native pair CLI
- **THEN** they present `houmao-mgr agents prompt ...` as the default documented path
- **AND THEN** they present `houmao-mgr agents gateway prompt ...` as the explicit gateway-managed alternative rather than the default

## ADDED Requirements

### Requirement: `houmao-mgr agents gateway prompt` returns structured JSON send results and refusal errors

`houmao-mgr agents gateway prompt` SHALL return structured JSON describing prompt dispatch outcome.

On success, the command SHALL print a JSON success payload stating that the prompt was sent.

When the live gateway refuses prompt control because the target is not ready, already busy, unavailable, unsupported, or otherwise cannot accept the prompt, the command SHALL print a structured JSON error payload and SHALL exit non-zero.

The command SHALL accept `--force`, which forwards `force = true` to the live gateway prompt-control route.

#### Scenario: Ready prompt dispatch prints JSON success

- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..."`
- **AND WHEN** the addressed target is prompt-ready
- **THEN** the command prints structured JSON reporting that the prompt was sent
- **AND THEN** the command exits successfully

#### Scenario: Not-ready prompt refusal prints JSON error and exits non-zero

- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..."`
- **AND WHEN** the addressed target is not prompt-ready
- **AND WHEN** the operator did not pass `--force`
- **THEN** the command prints a structured JSON error payload
- **AND THEN** the command exits non-zero

#### Scenario: Force forwards prompt control override semantics

- **WHEN** an operator runs `houmao-mgr agents gateway prompt --agent-id abc123 --prompt "..." --force`
- **THEN** `houmao-mgr` forwards that request as forced prompt control
- **AND THEN** the command does not reject the prompt only because the target was not prompt-ready before dispatch
