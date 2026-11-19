# RC3 Iteration 2 G0, H1 Preparation, and P1

Date: 2026-11-19. Status: G0 passed for the H1 Qwen start; H1 materials prepared from physical checkout `tmp/` storage, launched, and P1 completed through the signed gateway. R0 has one passing negative case. P2–P4 remain pending.

Plan: [Iteration 2](../iterations/2026-11-19-plan-2-dsh-rc3-run-modes.md). Question: [KQ-1](../key-questions/KQ-1-dsh-basic-functionality.md).

## Release and Provider Checks

- `pixi run houmao-mgr --version` returned `houmao-mgr, version 3.0.0rc3`.
- The explicitly selected `tmp/dsh/npm-runtime/node_modules/.bin/dsh --version` returned `0.2.2-rc.3`.
- `GET http://127.0.0.1:14888/v1/models` returned `Qwen/Qwen3.8-27B-FP8` with `max_model_len: 262144`.
- The offline fixture configuration resolved to backend `dsh_headless`, mode `headless`, surface `manager`, adapter `pi-ai`, protocol `openai-completions`, and endpoint-only authentication.
- The prepared-run offline check returned `status: prepared` and `prerequisites.missing: []`.

## Isolation and RC2 Containment

The previous RC2 B1 session `HOUMAO-dsh-qwen38-acp-rc2-1795064736492` remained present on its separate socket `/data/huangzhe/code/houmao/tmp/houmao-30-iter1-rc2/tsock/tmux-1001/default`. No RC3 command was issued against that agent or its manifests, and the session was not stopped or modified.

A new disposable tmux server was created with a unique `/tmp/tmux-1001/houmao-30-iter2-g0-*` socket after clearing `TMUX`, `TMUX_PANE`, and `TMUX_TMPDIR`. Session `g0-smoke` was listed successfully, and only that explicit isolated server was killed. The default server still contained `mao-1` through `mao-4`, `rsi-1` through `rsi-4`, and `sys` after the check.

## Launch Material Location

All generated test materials are accessible under the consolidated `tmp/` root. The H1 access path is:

```text
/data/huangzhe/code/houmao/tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-headless-manager-4098c41338ef
```

The checkout-`tmp` storage-policy fix now permits purpose-specific run roots inside the Git-ignored scratch tree. `tmp/houmao-30-iter2-rc3/` is a real directory, and the current run's physical files and `run.json` paths all remain under it. The earlier symlink workaround was retired. See the [storage-policy fix log](../logs/2026-11-19-checkout-tmp-storage-policy-fix.md).

Important paths within that run:

| Path | Purpose |
| --- | --- |
| `run.json` | Sanitized run identity, selected configuration, executable, project paths, and isolated tmux selector |
| `assets/roles/server-api-smoke/system-prompt.md` | Materialized role containing literal `{{ITER1_LITERAL}}` and `$KEEP_LITERAL` |
| `assets/tools/dsh/setups/fixture/tool-params.yaml` | Qwen model, endpoint environment reference, protocol, reasoning map, and compatibility metadata |
| `home/` | Private native DSH home, including `houmao-role.txt`, `houmao-tool-params.yaml`, and `houmao-profile.patch.json` |
| `workdir/.houmao/` | Managed project overlay with the `fixture-agent` specialist, preset, role, credential reference, and catalog |
| `bin/tmux` | Fixture shim binding runtime tmux calls to the run's isolated server |
| `private-env.json` | Private process environment; contents were not read or copied into this evidence |

The run reports tmux socket `/tmp/tmux-1001/houmao-fixture-self-hosted-dsh-headless-manager-4098c41338ef`. Session `HOUMAO-self-hosted-dsh-headless-manager-4098c41338ef-1795084663404` is active on that isolated server. The executable attach wrapper is `tmp/houmao-30-iter2-rc3/attach-h1.sh`.

The canonical role input used for subsequent Iteration 2 DSH arms is `tmp/houmao-30-iter2-rc3/inputs/iter2_dsh_system_prompt.txt`. The consolidated `tmp/houmao-30-iter2-rc3/` hierarchy physically contains generated inputs, complete fixture runs, non-secret wrappers, and observations.

## Commands and Results

Offline configuration validation used the selected Qwen parameters and returned `status: configuration_valid`:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check \
  --case self-hosted --client dsh --mode headless --surface manager \
  --model Qwen/Qwen3.8-27B-FP8 --base-url http://127.0.0.1:14888/v1 \
  --context-window 262144 --max-output-tokens 8192 \
  --dsh-reasoning '{"off":"none","low":"low","medium":"medium","high":"high"}' \
  --dsh-compat '{"supports_developer_role":false}'
```

Preparation used the same parameters plus:

```bash
  --system-prompt-file scripts/explore/houmao-3-0-interactive-review/iter2_dsh_system_prompt.txt \
  --run-root "$HOME/.local/state/houmao-30-iter2-rc3/runs" \
  --executable /data/huangzhe/code/houmao/tmp/dsh/npm-runtime/node_modules/.bin/dsh
```

The prepared-run check was:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py check \
  --run-dir /home/huangzhe/.local/state/houmao-30-iter2-rc3/runs/self-hosted-dsh-headless-manager-93aaf19e0759
```

The R0 negative mode check used `--mode tui`. It was rejected before launch as expected:

```json
{"error": "Tool 'dsh' does not support mode 'tui'. Supported modes: headless, service, web."}
```

## Corrections and Failures

1. **Plan root corrected before preparation.** The initial revision placed fixture project state under `tmp/houmao-30-iter2-rc3/`, but source inspection showed that `fixturelib.auth.validate_external_path()` rejects private run state inside the checkout. The first preparation therefore used the direct external `runs/` path and kept only non-secret wrappers in the repository scratch directory.
2. **Unsupported offline-check option.** The first offline `fixture.py check` included `--executable`. The argument parser rejected it because that option belongs to `prepare`, not `check`. Removing it produced `configuration_valid`. The executable was separately version-checked and then supplied to `prepare`, which resolved it to the selected DSH `bin.js` and reported no missing prerequisites.
3. **Generated materials consolidated under `tmp/` after preparation.** Operator direction required all generated testing materials under one `tmp/<subdir>` hierarchy. The empty `tmp/houmao-30-iter2-rc3/` directory was replaced with a symlink to the existing external campaign root, and the shared role moved to `tmp/houmao-30-iter2-rc3/inputs/iter2_dsh_system_prompt.txt`. This gives every generated input and runtime artifact one `tmp/` access path without disabling the fixture's resolved-path safety check. `fixture.py check --run-dir /data/huangzhe/code/houmao/tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-headless-manager-93aaf19e0759` then returned `status: prepared` with no missing prerequisites.

4. **Physical `tmp/` storage implemented.** After the operator explicitly requested a code fix, the fixture and gateway storage policies were changed to allow purpose-specific checkout `tmp/` run roots. The fixed fixture created `self-hosted-dsh-headless-manager-4098c41338ef` directly under the real `tmp/houmao-30-iter2-rc3/` directory. The superseded external preparation was removed, and the new run passed offline loading with no missing prerequisites. See the [storage-policy fix log](../logs/2026-11-19-checkout-tmp-storage-policy-fix.md).

The preparation arguments recorded above are the original commands. Future prepare and launch commands use the consolidated physical `tmp/` paths.

## Live P1 Result and Next Command

H1 launched successfully from the physical `tmp/` run. The authenticated gateway dispatched P1, the pane showed `{{ITER1_LITERAL}} $KEEP_LITERAL OK` and `[complete] native_completed`, and signed usage recorded `turn-2d66cb64e363` as completed with 6,786 total tokens. The agent is `fd4e2343-7ed5-4346-8105-a645933fde83`, with native session `session-5b3b8aa7-7390-4245-bcda-d8183c4cd968` and gateway `http://127.0.0.1:38605`. A live signed check returned healthy usage collection and no missing prerequisites. The agent remains running for subsequent prompts.

The next planned step submits P2 without relaunching:

```bash
pixi run python scripts/agents/test-fixtures/fixture.py prompt \
  --run-dir /data/huangzhe/code/houmao/tmp/houmao-30-iter2-rc3/runs/self-hosted-dsh-headless-manager-4098c41338ef \
  --prompt 'Create a file named dsh_probe.txt in the current working directory containing exactly ONE-LINE-OK, then run pwd and reply with DONE.'
```
