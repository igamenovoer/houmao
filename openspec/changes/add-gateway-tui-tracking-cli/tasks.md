## 1. Shared Tracking History

- [ ] 1.1 Add shared TUI snapshot-history models for bounded recent tracked snapshots and their response envelope.
- [ ] 1.2 Extend the shared TUI tracking runtime to record recent tracked snapshots in memory and evict the oldest entries beyond the internal 1000-snapshot cap.
- [ ] 1.3 Keep current-state `recent_transitions` behavior intact while making snapshot history available as a separate tracker read path.

## 2. Gateway and Pair Routes

- [ ] 2.1 Update the direct gateway client and service to serve raw TUI state, bounded snapshot history, and prompt-note tracking through the TUI control routes.
- [ ] 2.2 Add `houmao-server` managed-agent gateway TUI proxy routes, service methods, and pair-client methods for `tui/state`, `tui/history`, and `tui/note-prompt`.
- [ ] 2.3 Add matching `houmao-passive-server` gateway TUI proxy routes and client/service support with the same managed-agent resolution and no-gateway error behavior as existing gateway proxy routes.

## 3. `houmao-mgr` CLI Surface

- [ ] 3.1 Add the `houmao-mgr agents gateway tui` subgroup with `state`, `history`, `watch`, and `note-prompt` commands.
- [ ] 3.2 Reuse the existing managed-agent selector and current-session resolution contract for all new gateway TUI commands across local resumed-controller and pair-backed paths.
- [ ] 3.3 Implement `watch` as CLI-side polling over the raw gateway-owned TUI state path without introducing a new streaming transport.

## 4. Verification and Documentation

- [ ] 4.1 Add tests for tracker snapshot retention, including the 1000-entry eviction boundary.
- [ ] 4.2 Add server, passive-server, and CLI tests covering the new gateway TUI routes, command help, target resolution, and prompt-note behavior.
- [ ] 4.3 Update CLI, gateway, and managed-agent API docs to document the new `agents gateway tui` surface and clarify that its history is bounded in-memory snapshot history rather than coarse managed-agent `/history`.
