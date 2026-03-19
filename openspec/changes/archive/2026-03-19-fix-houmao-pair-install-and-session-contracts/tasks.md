## 1. Server Contract

- [x] 1.1 Add typed session-detail and session-terminal-summary models for `GET /sessions/{session_name}` and wire them into the CAO/Houmao client helpers.
- [x] 1.2 Add request/response models plus a `houmao-server` install surface for pair-owned profile installation against child-managed CAO state.
- [x] 1.3 Implement the server-side install execution path so it resolves child-managed state internally and returns explicit success or failure without exposing child-home paths.

## 2. Pair CLI Behavior

- [x] 2.1 Extend `houmao-srv-ctrl install` with additive `--port` handling that targets a supported `houmao-server` pair instance instead of ambient local `HOME`.
- [x] 2.2 Update `houmao-srv-ctrl launch` and delegated runtime artifact materialization to consume the typed session-detail contract and preserve tmux window identity when available.
- [x] 2.3 Remove consumer-side child-home derivation from the Houmao dual shadow-watch demo and any related helper flows that currently compute hidden child paths directly.

## 3. Verification And Docs

- [x] 3.1 Add unit and integration coverage for pair-targeted install success/failure, unsupported-pair rejection, typed session-detail parsing, and tmux-window preservation on launch.
- [x] 3.2 Update pair reference and migration docs to document the pair-owned install path and reaffirm that `child_cao` storage remains internal implementation detail.
- [x] 3.3 Re-run the Houmao dual shadow-watch demo or autotest path against the pair-owned install flow and capture any remaining follow-up gaps.
