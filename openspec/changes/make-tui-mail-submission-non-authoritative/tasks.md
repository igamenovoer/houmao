## 1. Authority-Aware Mail Result Contract

- [ ] 1.1 Define a shared mailbox command result envelope that distinguishes verified execution from non-authoritative TUI submission outcomes
- [ ] 1.2 Update manager mail command models and serializers so TUI-mediated paths can return `submitted` / `rejected` / `busy` / `interrupted` / `tui_error` without claiming mailbox success
- [ ] 1.3 Preserve authoritative mailbox success and failure reporting for manager-owned direct execution and gateway-backed execution paths

## 2. Local Manager And Runtime Routing

- [ ] 2.1 Refactor local `houmao-mgr agents mail ...` routing so manager-owned direct execution remains preferred and TUI fallback downgrades to submission-only semantics
- [ ] 2.2 Update runtime mail command handling so TUI-mediated mailbox flows do not require exact sentinel-schema recovery to complete a manager command
- [ ] 2.3 Keep TUI parsing available for readiness, busy-state detection, and optional preview or diagnostics without using it as the authoritative mailbox correctness boundary

## 3. Documentation And Regression Coverage

- [ ] 3.1 Update mailbox contract and operations docs to explain authoritative versus non-authoritative mailbox command outcomes and the supported verification paths
- [ ] 3.2 Add regression coverage for local TUI-mediated mail commands showing that a submitted request can return without exact mailbox-result parsing
- [ ] 3.3 Add regression coverage for verified manager-owned execution paths to ensure authoritative mailbox success and failure semantics remain intact
