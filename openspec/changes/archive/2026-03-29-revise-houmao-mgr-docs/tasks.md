## 1. Type A — Correct Wrong Flag Names

- [x] 1.1 In `docs/reference/cli/houmao-mgr.md`, update the `brains build` options table: rename `--recipe` → `--preset`, `--config-profile` → `--setup`, `--cred-profile` → `--auth`, and update description text to match
- [x] 1.2 In `docs/reference/houmao_server_pair.md`, update the representative brains build example command to use `--setup dev --auth openai` instead of `--config-profile dev --cred-profile openai`

## 2. Type B — Rewrite Operator Reference Docs to Use houmao-mgr as Primary Surface

- [x] 2.1 Rewrite `docs/reference/agents/contracts/public-interfaces.md`: replace `python -m houmao.agents.realm_controller send-prompt` and `stop-session` examples with `houmao-mgr agents prompt` and `houmao-mgr agents stop`; add a "Low-level access" section that retains the raw module examples with a note that manifest-path control and name-based tmux control remain the underlying model
- [x] 2.2 Rewrite `docs/reference/registry/operations/discovery-and-cleanup.md`: replace raw `realm_controller` CLI examples in the discovery walkthrough with `houmao-mgr agents prompt --agent-name <name>` and `houmao-mgr agents stop --agent-name <name>`; retain discovery model explanation and diagrams; add a "Low-level access" section for raw module invocations
- [x] 2.3 Rewrite `docs/reference/realm_controller_send_keys.md`: add a new introduction paragraph naming `houmao-mgr agents gateway send-keys` as the current operator surface; add a note that the raw `realm_controller send-keys` subcommand was `cao_rest`-backend-only; move the raw module usage section to a "Low-level access" block; preserve the key grammar and escape token documentation (it is shared by gateway send-keys)

## 3. Type C — Document Stalwart Access Gap

- [x] 3.1 In `docs/reference/mailbox/operations/stalwart-setup-and-first-session.md`, add a callout note near the top of the setup workflow section stating that `--mailbox-transport stalwart` is not currently exposed via `houmao-mgr agents launch`; keep all existing `python -m houmao.agents.realm_controller start-session` examples intact

## 4. Type D — Update Mermaid Diagrams to Use houmao-mgr Verbs

- [x] 4.1 In `docs/reference/agents/operations/session-and-message-flows.md`, update all Mermaid sequence diagrams: replace `start-session` → `houmao-mgr agents launch`, `send-prompt` → `houmao-mgr agents prompt`, `stop-session` → `houmao-mgr agents stop`; update any prose that references the old command names
- [x] 4.2 In `docs/reference/gateway/operations/lifecycle.md`, update the Mermaid sequence diagram that shows `start-session --gateway-auto-attach` to show `houmao-mgr agents launch` + `agents gateway attach`; update any prose references
- [x] 4.3 In `docs/reference/registry/internals/runtime-integration.md`, update `send-prompt` and `stop-session` references in diagrams and explanatory prose to `houmao-mgr agents prompt` and `houmao-mgr agents stop`
- [x] 4.4 In `docs/reference/agents/internals/state-and-recovery.md`, update the `stop-session` mention to `houmao-mgr agents stop`
- [x] 4.5 In `docs/reference/mailbox/operations/common-workflows.md`, update the `start-session` mention to `houmao-mgr agents launch`

## 5. Type E — Minor Stale Reference

- [x] 5.1 In `docs/reference/system-files/roots-and-ownership.md`, update the table row that reads "`build-brain` exposes `--runtime-root`" to "`houmao-mgr brains build` exposes `--runtime-root`"

## 6. Verification

- [x] 6.1 Run `grep -rn "config-profile\|cred-profile\|--recipe\b" docs/` and confirm zero matches remain outside of explicitly-deprecated or historical notes
- [x] 6.2 Run `grep -rn "python -m houmao.agents.realm_controller" docs/` and confirm all matches are inside clearly-labelled low-level or advanced sections, or in documents that are explicitly scoped as module-level developer reference (e.g., stalwart setup)
- [x] 6.3 Run `grep -rn "start-session\|send-prompt\|stop-session" docs/` and confirm all remaining matches are either in legacy/deprecated notices, the `cli.md` index listing, or in the retained low-level sections
- [x] 6.4 Spot-check that Mermaid diagrams in the five updated files render correctly in a local `mkdocs serve` or GitHub preview
