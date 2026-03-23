## 1. Server TUI Tracking Foundation

- [x] 1.1 Add server-owned TUI tracking modules and models for internal tracked-session identity, `terminal_id` compatibility aliases, probe snapshots, explicit transport/process/parse state, stability metadata, and bounded recent transitions
- [x] 1.2 Add a known-session registry plus supervisor lifecycle that seeds from server-owned registration records, enriches entries with manifest-backed metadata, verifies tmux liveness, and integrates with `houmao-server` startup and shutdown
- [x] 1.3 Add configuration surfaces for tracking poll interval, supported-process detection, and bounded recent-transition retention

## 2. Direct Tmux And Process Observation

- [x] 2.1 Implement tmux transport probes by reusing or promoting shared `tmux_runtime` helpers to resolve the tracked tmux session or pane and capture pane text directly from tmux
- [x] 2.2 Implement process inspection for tracked panes so the server can determine supported TUI up/down state from the live process tree
- [x] 2.3 Wire watch-worker lifecycle so tmux loss stops workers while TUI-down sessions remain tracked

## 3. Official Parser And Continuous Reduction

- [x] 3.1 Add a server-owned official parser adapter that uses the shared parser stack without CAO-specific wrappers
- [x] 3.2 Port or refactor the existing parser reduction logic into a continuous in-memory live tracker for explicit transport/process/parse state, parsed surface state, derived operator state, and stability timing
- [x] 3.3 Remove CAO terminal-status and terminal-output polling from the parsing and state-tracking path inside `houmao-server`

## 4. In-Memory Server State Surfaces

- [x] 4.1 Replace file-backed watch snapshot and watch-log internals with an in-memory authoritative state store and bounded recent-transition history
- [x] 4.2 Update `houmao-server` extension models and routes to keep the existing terminal-keyed v1 lookup surface while exposing explicit transport/process/parse state, operator-facing live state, stability metadata, and recent transitions from memory
- [x] 4.3 Update session registration and startup rediscovery so server-owned registration is the primary discovery seed, manifest metadata enriches tracked identity, tmux verifies liveness, and shared registry remains compatibility evidence only

## 5. Verification

- [x] 5.1 Add unit tests for tmux probing, process-based TUI up/down detection, and known-session worker lifecycle
- [x] 5.2 Add parser integration and reducer tests covering direct tmux capture, parse failures, explicit transport/process/parse contract fields, stability metadata, and bounded recent transitions
- [x] 5.3 Add server tests proving that live parsing and state tracking no longer depend on child `cao-server` output or status endpoints

## 6. Documentation And Change Hygiene

- [x] 6.1 Update `houmao-server` reference and migration docs to describe official server-owned TUI parsing, registration-seeded discovery, terminal-keyed compatibility lookup, and in-memory live tracking
- [x] 6.2 Narrow the overlapping `add-shadow-watch-state-stability-window` change to demo-only visualization or other consumption of the server-owned tracker contract, or otherwise mark it superseded for contract-setting semantics
