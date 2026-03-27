## 1. README Updates

- [x] 1.1 Update the "How Agents Join Your Workflow" paragraph in `README.md` (line 48-51) to describe `agents join` as a working first-class adoption path instead of a future design goal, mentioning both managed launch and bring-your-own-process join as working paths.
- [x] 1.2 Add a new "Quick Start: Adopt an Existing Session" section to `README.md` before the current Section 3 "Basic Workflow", containing: a brief intro explaining that `agents join` is the zero-setup entry point, a Mermaid sequence diagram showing the join pipeline (operator → tmux → provider TUI → `agents join` → managed agent envelope with manifest + gateway + registry), and three concrete command examples (minimal TUI join, TUI join with relaunch options, headless join).
- [x] 1.3 Add a "What You Get After Joining" subsection documenting: shared registry discovery (`houmao-mgr agents state`), prompt submission (`houmao-mgr agents prompt`), interrupt (`houmao-mgr agents interrupt`), gateway attach (`houmao-mgr agents gateway attach`), mailbox registration (`houmao-mgr agents mailbox register`), and stop (`houmao-mgr agents stop`).
- [x] 1.4 Update the README Architecture Mermaid flowchart to include the `agents join` path as an alternative entry alongside `agents launch`, showing that join wraps an existing process while launch builds and starts one.

## 2. Demo Pack Structure

- [x] 2.1 Create the demo pack directory `scripts/demo/agents-join-demo-pack/` with a `README.md` documenting prerequisites (tmux, pixi, a working Claude Code or Codex CLI), quick start commands, step-by-step walkthrough, expected outputs at each stage, and a Mermaid sequence diagram of the demo lifecycle.
- [x] 2.2 Create `scripts/demo/agents-join-demo-pack/run_demo.sh` orchestrator script that accepts an optional `--provider` argument (default `claude_code`), validates prerequisites (tmux, provider CLI), and sequences the individual step scripts with error handling and non-zero exit on failure.

## 3. Demo Pack Step Scripts

- [x] 3.1 Create `scripts/demo/agents-join-demo-pack/start_provider.sh` that starts a new tmux session with the selected provider TUI running in window 0, pane 0, and waits for the provider process to become visible in the pane process tree.
- [x] 3.2 Create `scripts/demo/agents-join-demo-pack/join_session.sh` that runs `houmao-mgr agents join --agent-name <demo-name>` from inside the demo tmux session and validates the join result output (agent_name, manifest_path, backend fields).
- [x] 3.3 Create `scripts/demo/agents-join-demo-pack/inspect_state.sh` that runs `houmao-mgr agents state --agent-name <demo-name>` and verifies the joined agent appears in the shared registry with the expected provider and backend.
- [x] 3.4 Create `scripts/demo/agents-join-demo-pack/stop_agent.sh` that runs `houmao-mgr agents stop --agent-name <demo-name>` and verifies the agent is no longer running.

## 4. Verification

- [x] 4.1 Run the demo pack end-to-end with the default provider to verify the scripts work and match the README expected outputs.
- [x] 4.2 Verify the README Mermaid diagrams render correctly in GitHub-flavored Markdown.
