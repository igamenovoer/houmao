## 1. Refresh the getting-started path

- [x] 1.1 Rewrite `docs/getting-started/quickstart.md` so it uses the current `houmao-mgr` managed-agent workflow (`brains build`, selector-based `agents launch`, selector-based prompting, and `agents stop`).
- [x] 1.2 Update `docs/getting-started/overview.md` so backend and CLI positioning match the current supported operator posture and current legacy wording.

## 2. Expand CLI reference coverage

- [x] 2.1 Update `docs/reference/cli/houmao-server.md` so the `serve`, `health`, `current-instance`, `register-launch`, `sessions`, and `terminals` sections match the live command tree and current `serve` flags.
- [x] 2.2 Update `docs/reference/cli/houmao-mgr.md` so its command-group summary matches the active CLI tree and links readers to the newer nested command families.
- [x] 2.3 Add dedicated CLI reference pages for `houmao-mgr agents gateway`, `houmao-mgr agents turn`, `houmao-mgr agents mail`, `houmao-mgr agents mailbox`, and `houmao-mgr admin cleanup`.

## 3. Correct stale runtime and subsystem references

- [x] 3.1 Update `docs/reference/run-phase/session-lifecycle.md` and any directly related run-phase pages so session-root, manifest, job-dir, and legacy-backend guidance match the current implementation.
- [x] 3.2 Correct stale runtime and agent reference pages including `docs/reference/realm_controller.md`, `docs/reference/realm_controller_send_keys.md`, and `docs/reference/agents/operations/session-and-message-flows.md`.
- [x] 3.3 Align gateway and mailbox reference pages with the current current-session attach rules, `gateway/run/current-instance.json` authority, late mailbox registration flow, and `resolve-live` discovery guidance.

## 4. Cross-link and verify the updated docs

- [x] 4.1 Update `docs/reference/index.md`, `docs/reference/managed_agent_api.md`, and any other affected entry pages so the new CLI reference coverage is discoverable.
- [x] 4.2 Sweep the docs for stale command and contract wording such as `--session-id`, `agents terminate`, `join-tmux`, outdated job-dir manifest claims, and incomplete `houmao-server serve` flag coverage, then correct any remaining matches.
