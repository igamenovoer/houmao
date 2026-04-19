## 1. Spec And Publication Semantics

- [x] 1.1 Add a dedicated long finite tmux-backed sentinel TTL constant and update shared-registry lease selection so all tmux-backed records, including joined sessions, use it instead of the ordinary 24-hour TTL or the current 30-day joined-session sentinel.
- [x] 1.2 Preserve current non-tmux/no-publish behavior and explicit shared-registry teardown removal semantics without introducing a new non-tmux registry publication contract.
- [x] 1.3 Add or update targeted unit coverage for tmux-backed TTL selection, including freshness beyond the former 24-hour boundary and beyond the current 30-day joined-session boundary.

## 2. Discovery And Cleanup Verification

- [x] 2.1 Add or update registry storage and passive discovery tests proving tmux-backed records remain discoverable after the former lease boundaries when passive discovery's existing tmux-liveness check passes.
- [x] 2.2 Add or update cleanup tests proving a dead tmux-backed record is still removable via local tmux liveness probing despite the sentinel lease.
- [x] 2.3 Verify `_list_registry_records()` and `_resolve_local_managed_agent_record_with_miss_context()` or their CLI-facing tests continue to work without adding eager tmux probes to ordinary local discovery.
