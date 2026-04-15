## MODIFIED Requirements

### Requirement: V2 initialization writes participant memo material to houmao-memo
The packaged `houmao-agent-loop-pairwise-v2` initialization guidance SHALL use each targeted live participant's `houmao-memo.md` file for per-agent initialization memory when the participant exposes managed memo-pages memory.

The memo material SHALL include the participant's local role, local objective, allowed delegation targets or delegation set, task-handling rules, obligations, forbidden actions, mailbox and result-return expectations, and any routing-packet or child-dispatch references that the participant must keep easy to reopen across turns.

The v2 guidance SHALL direct initialization to write or append this material through the supported memory memo operation when available, using `HOUMAO_AGENT_MEMO_FILE` as the in-agent pointer and the gateway or pair-server memory memo endpoint as the operator-side entrypoint.

When initialization material is too large for the memo, the guidance SHALL allow a contained page under `HOUMAO_AGENT_PAGES_DIR` and SHALL rely on the memo pages index to make that page discoverable.

The v2 guidance SHALL NOT refer to scratch ledgers or persist lanes as current managed memory concepts.

#### Scenario: Initialization writes one participant memo
- **WHEN** `houmao-agent-loop-pairwise-v2` initializes participant `worker-a`
- **AND WHEN** `worker-a` exposes managed memo file `/repo/.houmao/memory/agents/worker-a-id/houmao-memo.md`
- **THEN** initialization records `worker-a`'s role, objective, delegation authority, obligations, forbidden actions, and result-return expectations in that memo file
- **AND THEN** it does not write that rule material to a scratch ledger

#### Scenario: Memo update uses supported memory surface
- **WHEN** the operator-side initialize action needs to update a live participant memo
- **AND WHEN** the participant has a live gateway or pair-server memory proxy
- **THEN** the v2 guidance uses the supported memory memo endpoint or CLI operation
- **AND THEN** it does not ask the participant to infer the initialization rules from prior email alone
