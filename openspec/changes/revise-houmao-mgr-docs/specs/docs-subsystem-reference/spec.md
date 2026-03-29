## MODIFIED Requirements

### Requirement: Registry reference retains current content with accuracy pass

The registry reference SHALL retain existing content with a light accuracy pass: verify that `ManagedAgentRecord`, `LiveAgentRecord`, and filesystem registry operations match `registry_models.py` and `registry_storage.py` source. Remove any stale CAO references.

Operator-facing pages within the registry reference (notably `operations/discovery-and-cleanup.md`) SHALL use `houmao-mgr agents prompt` and `houmao-mgr agents stop` as the primary example commands for name-based session control. Raw `python -m houmao.agents.realm_controller` invocations MAY be retained in a clearly-labelled low-level section but SHALL NOT appear as the primary examples.

#### Scenario: Registry docs match current models

- **WHEN** comparing registry reference docs to `registry_models.py` exports
- **THEN** the documented record fields and operations match the source

#### Scenario: Registry operations examples use houmao-mgr as primary surface

- **WHEN** a reader follows an example in `registry/operations/discovery-and-cleanup.md` to send a prompt or stop a session by agent name
- **THEN** the primary example uses `houmao-mgr agents prompt --agent-name <name>` or `houmao-mgr agents stop --agent-name <name>`
- **AND THEN** any raw module invocation appears in a section explicitly labelled as low-level or advanced access

## ADDED Requirements

### Requirement: Operator-facing agent reference uses houmao-mgr as primary example surface

`docs/reference/agents/contracts/public-interfaces.md` and `docs/reference/agents/operations/session-and-message-flows.md` SHALL present `houmao-mgr agents` commands as the primary operator surface. Any raw `python -m houmao.agents.realm_controller` invocations SHALL be retained only in a clearly-labelled "Low-level access" section.

Mermaid sequence diagrams in these pages SHALL use `houmao-mgr agents launch`, `houmao-mgr agents prompt`, and `houmao-mgr agents stop` (with appropriate `<br/>` wrapping for width) rather than the abstract `start-session`, `send-prompt`, and `stop-session` verb forms.

#### Scenario: Reader copies a prompt example from public-interfaces.md

- **WHEN** a reader reads the session targeting or control surface examples in `agents/contracts/public-interfaces.md`
- **THEN** the first example shown is `houmao-mgr agents prompt --agent-name <name> --prompt "<text>"`
- **AND THEN** raw `python -m houmao.agents.realm_controller send-prompt` appears only in a low-level section below the primary content

#### Scenario: Session lifecycle diagram uses houmao-mgr verbs

- **WHEN** a reader views the session lifecycle sequence diagram in `agents/operations/session-and-message-flows.md`
- **THEN** the diagram labels show `houmao-mgr agents launch`, `houmao-mgr agents prompt`, and `houmao-mgr agents stop`
- **AND THEN** no `start-session`, `send-prompt`, or `stop-session` labels appear in the diagram

### Requirement: send-keys reference reframed around gateway send-keys

`docs/reference/realm_controller_send_keys.md` SHALL introduce `houmao-mgr agents gateway send-keys` as the current operator surface for raw control input. The document SHALL note that the raw `realm_controller send-keys` subcommand was `cao_rest`-only and is no longer the primary access path. Raw module examples MAY be retained in a low-level section.

#### Scenario: Reader learns where to send raw key sequences today

- **WHEN** a reader opens `docs/reference/realm_controller_send_keys.md`
- **THEN** the introduction identifies `houmao-mgr agents gateway send-keys` as the current operator surface
- **AND THEN** the reader is not required to read to the end of the page to discover the houmao-mgr equivalent

### Requirement: Gateway lifecycle diagram uses houmao-mgr verbs

The Mermaid sequence diagram in `docs/reference/gateway/operations/lifecycle.md` SHALL use `houmao-mgr agents launch` (or `agents gateway attach`) rather than `start-session --gateway-auto-attach`. Other abstract runtime verbs in that diagram SHALL also use their `houmao-mgr` equivalents.

#### Scenario: Gateway lifecycle diagram is consistent with current CLI

- **WHEN** a reader views the gateway lifecycle sequence diagram
- **THEN** the diagram does not show `start-session` as the operator action
- **AND THEN** the diagram shows a `houmao-mgr`-based launch + gateway action instead

### Requirement: Stalwart setup doc names the houmao-mgr access gap

`docs/reference/mailbox/operations/stalwart-setup-and-first-session.md` SHALL include a prominent note near the start of the workflow section stating that `--mailbox-transport stalwart` is not currently exposed via `houmao-mgr agents launch`, and that the raw `python -m houmao.agents.realm_controller start-session` path remains the supported access route for the stalwart mailbox workflow.

#### Scenario: Reader understands they cannot use houmao-mgr for stalwart sessions today

- **WHEN** a reader opens the stalwart setup and first-session guide
- **THEN** they see a clearly-worded note before the first code example that `houmao-mgr agents launch` does not yet expose `--mailbox-transport stalwart`
- **AND THEN** the existing `python -m houmao.agents.realm_controller start-session` examples remain intact as the correct access path
