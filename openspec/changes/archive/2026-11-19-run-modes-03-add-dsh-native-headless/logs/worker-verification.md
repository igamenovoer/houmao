# Native Worker Verification

The managed bridge starts a fresh process for each prompt. Its Python setup replaces itself with the qualified DSH executable, so the bridge keeps the actual worker's process ID and birth token. The launcher receives its profile patches before the headless application arguments. Prompt bytes travel through an unlinked private stdin file. The per-attempt command and dispatch permission contain no prompt bytes.

The DSH companion checks the current owner reservation, generation, caller process, attempt ID, and revocable permission in the synchronous `followup` path. It writes the admission receipt after DSH inserts that message in the native inbox. That insertion supplies the admission evidence even when DSH publishes a session earlier. A missing saved native session fails exact continuation and preserves the requested identity for diagnosis.

The bridge publishes successful exit only after it verifies the native `final` record, the owned handoff, and the corresponding terminal record in the flushed native journal. Public diagnostics use bounded, redacted text. Raw stdout and stderr stay in private files. A controller wait timeout after handoff leaves the worker and its attempt pending for recovery.

The live interruption test found that DSH `0.2.2-rc.3` can catch `SIGTERM`, leave the turn unfinished, and return operating-system code zero. The bridge now requires a delivered signal receipt for the exact pinned worker and observes process cleanup. It reports managed interruption with `source=owner_process` when a verified completed final is absent. The bridge also adopts and reaps detached Linux children that DSH can start in their own process groups. This cleanup uses Linux process handles and child subreaping.

## Results

| Check | Result |
| --- | --- |
| `0.2.2-rc.3` with self-hosted Qwen `Qwen/Qwen3.8-27B-FP8` | Two completed prompts produced `HEADLESS_FIRST` and `HEADLESS_SECOND` in distinct worker processes with the same native session and journal. |
| Controlled native startup fence | Two passed. The test held `agent/created`, revoked the permission or ended the caller, and confirmed that the inbox and provider saw no input. A later prompt reached the provider once with literal shell metacharacters and a newline. The fixture also removed the saved journal temporarily and verified that exact continuation refused before sending another provider request. |
| Live Qwen shell interruption | The manager observed a native shell tool, interrupted its captured owner, and reported `interrupted`. The bridge recorded raw code zero and verified managed code 130. A later prompt finished in a different worker under the same native session. |
| Worker and owner units | 20 passed. Cases include incomplete stdout, a controller wait timeout, a stale process identity, bounded escalation, and cleanup of a sleeping detached child. |
| Shared dispatch control units | 19 passed. The private permission now carries the exact attempt ID. |

Use the repository-selected DSH executable when repeating the controlled native tests. The fixture uses its recorded tmux socket and an explicit local provider endpoint.

```bash
env -u TMUX -u TMUX_PANE \
  HOUMAO_DSH_EXECUTABLE="$PWD/tmp/dsh/npm-runtime/node_modules/.bin/dsh" \
  pixi run pytest -q tests/integration/agents/dsh/test_headless_dispatch_permission.py

env -u TMUX -u TMUX_PANE pixi run pytest -q \
  tests/unit/agents/realm_controller/test_dsh_headless_worker.py \
  tests/unit/agents/realm_controller/test_headless_runner.py \
  tests/unit/agents/realm_controller/test_owner_admission.py \
  tests/unit/agents/realm_controller/test_plugin_dispatch_control.py
```
