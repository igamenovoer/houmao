## Why

The initial Step 5 passive-server implementation landed the new routes and basic service structure, but review found several correctness gaps that leave key workflows non-operational or non-resumable. We need a focused follow-up change now so `houmao-passive-server` can actually support the Step 5 launch, request, turn, interrupt, stop, and restart-recovery flows it is supposed to own.

## What Changes

- Fix `POST /houmao/agents/headless/launches` so server-launched headless agents are explicitly published to the shared registry and become addressable by later passive-server routes.
- Normalize managed-headless identity handling so follow-up `/turns`, `/interrupt`, and `/stop` requests can reliably find server-managed headless agents whether callers use tracked ids or published agent ids.
- Restore startup rebuild behavior by resuming `RuntimeSessionController` handles for live persisted headless sessions instead of rebuilding read-only placeholders.
- Reconcile completed turn records from persisted runtime artifacts so status, events, stdout, and stderr endpoints return durable data instead of empty results or false 404s.
- Tighten headless launch validation so the passive server checks manifest tool compatibility, validates optional role input, returns contract-matching client errors, and forwards the full mailbox option set including Stalwart fields.
- Update tests to cover registry publication, resumed control after restart, artifact persistence, identity lookup, and launch validation failures.

## Capabilities

### New Capabilities
- `passive-server-request-submission`: Passive-server request, interrupt, and stop behavior for Step 5, including correct routing to server-managed headless agents after launch.
- `passive-server-headless-management`: Passive-server headless launch, restart recovery, turn persistence, artifact retrieval, and launch validation behavior for Step 5.

### Modified Capabilities

## Impact

- **Code**: `src/houmao/passive_server/headless.py`, `src/houmao/passive_server/service.py`, and related passive-server tests; may reuse more of the existing old-server managed-headless reconciliation patterns.
- **APIs**: No new endpoints, but several existing Step 5 endpoints change from partially working to fully operational and contract-compliant.
- **Runtime behavior**: Server-launched headless agents become discoverable after launch and remain operable after passive-server restart.
- **Persistence**: Managed turn records will persist artifact metadata and completion evidence needed by status, event, and artifact endpoints.
