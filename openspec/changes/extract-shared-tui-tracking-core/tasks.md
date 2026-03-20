## 1. Shared Core Extraction

- [ ] 1.1 Create the new shared TUI tracking core package with neutral tracked-state models, normalized reducer inputs, and an official/runtime detector boundary below `server` and `explore`
- [ ] 1.2 Extract or move tracked-state reduction, turn-signal interpretation, and official/runtime detector ownership out of `houmao.server.tui` and adapter-owned packages into the shared core
- [ ] 1.3 Add focused unit tests for shared-core reduction covering explicit-input authority, surface inference, degraded diagnostics, and settled-success timing

## 2. Live Server Adaptation

- [ ] 2.1 Refactor the official live tracker to use the shared core while preserving server-owned tmux/process/probe observation and in-memory authority
- [ ] 2.2 Adapt `houmao.server.models` and related server state adapters around the neutral tracked-state model ownership chosen for the shared core while keeping `Houmao*` names as the explicit server route boundary
- [ ] 2.3 Update server tracking tests to verify public `surface`, `turn`, `last_turn`, and stability behavior still matches the official contract after extraction

## 3. Replay And Harness Adaptation

- [ ] 3.1 Refactor `terminal_record` replay analysis to consume the shared core and remove direct imports from `houmao.demo.cao_dual_shadow_watch`
- [ ] 3.2 Update recorder replay outputs, `terminal_record add-label`, label schema, and tests so the primary replay contract uses diagnostics plus `surface` / `turn` / `last_turn` semantics
- [ ] 3.3 Refactor the Claude state-tracking explore harness replay path to use a harness-owned adapter over the shared core while keeping the content-first groundtruth path separate
- [ ] 3.4 Update explore-harness replay and comparison tests to assert shared-core-backed behavior and expected timeline parity

## 4. Cleanup And Validation

- [ ] 4.1 Remove generic/runtime dependencies on the independent demo tracker while preserving the demo as a separate reference implementation
- [ ] 4.2 Add comparison coverage or fixtures that keep the demo tracker useful as an independent reference without making it an implementation dependency
- [ ] 4.3 Run focused test suites for server tracking, terminal-record replay, and Claude explore replay paths
- [ ] 4.4 Update relevant docs and developer references for the replay contract change, including any label-field or artifact examples that changed
