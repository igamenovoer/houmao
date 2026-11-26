# CCCC Deferred Mail Spec Delta

## MODIFIED Requirements

### Requirement: Mail Extends the Qualified CCCC Binding

Deferred Mail SHALL reuse the owner, Actor registration, credentials, and scoped references established by the CCCC integration. The selected gateway or direct CLI SHALL enable Mail only when it and the provider advertise the qualified Mail operations, limits, cursor, and read-reconciliation contract.

#### Scenario: Chat Works but Provider Lacks Read Reconciliation

- **WHEN** a compatible chat service lacks the required consuming-read receipts
- **THEN** chat remains available and Mail read is reported unsupported
- **AND THEN** the integration does not fall back to unsafe native consuming reads

#### Scenario: Mail Package Upgrade Preserves Owner

- **WHEN** an operator upgrades the plugin and restarts only the gateway with the same binding
- **THEN** the agent ID, Actor, body PID, and conversation remain unchanged

#### Scenario: An Agent Reads Mail Without a Running Gateway

- **WHEN** an agent selects its private Actor profile with direct `houmao-cccc` and performs an explicit qualified Mail read
- **THEN** CCCC applies the same cursor precondition, bounded consumption, and caller operation ID semantics as a gateway-mediated read
- **AND THEN** the agent can reconcile the authoritative receipt through a later direct invocation

### Requirement: CCCC Mail Is Explicitly Selected Outside Email Slots

Mail requests SHALL explicitly select the CCCC plugin instance and current binding in gateway mode or the verified owner-bound Actor profile in direct mode. CCCC Mail SHALL NOT occupy or replace offline or online email, determine canonical mail identity, or become an implicit email transport. Neither successful operation nor provider outage SHALL bridge these channels.

#### Scenario: All Communication Systems Coexist

- **WHEN** an agent has offline email, online Stalwart email, and CCCC Mail
- **THEN** all remain separately selectable and canonical mail identity follows the configured email slots only

#### Scenario: Stalwart Is Unavailable

- **WHEN** the caller explicitly selects CCCC Mail during a Stalwart outage
- **THEN** supported CCCC operations remain usable without contacting Stalwart or changing canonical identity

#### Scenario: Email Send Has an Uncertain Outcome

- **WHEN** an email send might have succeeded before its connection failed
- **THEN** the integration does not mirror or retry that message through CCCC

### Requirement: Mail Notices Remain Deferred and Ordinary

CCCC Mail notices SHALL follow the provider's qualified bounded, content-free policy and immediate ordinary gateway admission. The gateway SHALL process typed Mail notices independently of chat batches and their staging capacity. Inspection or synchronization SHALL NOT consume Mail or schedule body work. Refused notices SHALL NOT be retained by the plugin, and notice delivery SHALL NOT execute email reset, compaction, or archive workflows.

#### Scenario: Notice Arrives While Body Is Busy

- **WHEN** a CCCC Mail notice reaches a busy body
- **THEN** it reports the ordinary readiness refusal without queueing or reading the batch
- **AND THEN** later body readiness alone does not replay that notice

#### Scenario: Notice Reaches a Ready Body

- **WHEN** a valid content-free notice is handed to a ready body
- **THEN** it identifies CCCC Mail and its selected binding without advancing the Mail cursor

#### Scenario: A Mail Notice Arrives During Chat Batching

- **WHEN** a qualified Mail notice becomes eligible while chat is accumulating or waiting at its staging limit
- **THEN** the gateway evaluates the notice through its separate immediate admission path without adding the notice to a chat batch
- **AND THEN** notice handling leaves both the chat batch boundary and the Mail cursor unchanged

#### Scenario: A Direct Client Pulls Ordinary Chat

- **WHEN** the agent uses direct `houmao-cccc` to pull chat while deferred Mail exists for the same Actor
- **THEN** the direct pull returns only eligible chat and leaves deferred Mail available for a separate explicit Mail read
