# Iteration 3 R10: Launch-Profile Defaults With xhigh Reasoning

Date: 2026-11-24. Status: stopped and replaced by [R11 Kimi config-backed effort](2026-11-24-iter3-two-agent-mail-r11-kimi-config-effort.md). Both agents launched from project launch profiles that default the Qwen 3.8 model to `xhigh` reasoning. No R10 prompt or mail was sent.

Previous run: [R9 coordination rules](2026-11-23-iter3-two-agent-mail-r9-coordination-rules.md).

## Purpose

R9 was launched with native default reasoning `off`. This run replaces R9 with a fresh pair whose launch profiles default both agents to `xhigh` for `Qwen/Qwen3.8-27B-FP8`, and verifies the effective native configuration rather than only the manager output.

No product code changed. All changes are campaign scratch state under the Git-ignored `tmp/` tree and this log.

## R9 Teardown

Both R9 notifiers were disabled, then both owned agents were stopped through their agent IDs. The stop results reported `success: true` and named the owned native Web hosts. Gateway ports `37605` and `37606` were free afterward.

```text
R9 DSH  stopped: dsh_web-20261123-114657Z-09eaa1f2
R9 Kimi stopped: kimi_web-20261123-114701Z-9ea3a97c
```

## R10 Root and Shared Authority

```text
tmp/houmao-30-iter3-mailbox-r10/
```

The root contains fresh `registry/`, `runtime/`, `mailbox/`, `runs/`, `inputs/`, and `bin/`. The shared filesystem mailbox was initialized once before launch:

```bash
HOUMAO_GLOBAL_MAILBOX_DIR="$ROOT/mailbox" houmao-mgr mailbox init \
  --mailbox-root "$ROOT/mailbox" --registry-root "$ROOT/registry"
```

Result: `status: ready`, protocol version `4`, mailbox root selected by explicit override. Without this step, launch failed with:

```text
Error: Failed to prepare mail bindings: registry .../r10/registry has no offline store; initialize it with houmao-mgr mailbox init
```

## Fixture Preparation

Both runs were prepared with the maintained fixture, self-hosted Qwen lane, `web` mode, manager surface, and the same three coordination rules file copied from R9:

```text
tmp/houmao-30-iter3-mailbox-r10/inputs/coordination-rules.txt
```

DSH preparation used the native reasoning slot map:

```json
{"off": "none", "low": "low", "medium": "medium", "xhigh": "xhigh"}
```

Kimi preparation used the fixture's direct thinking inputs:

```text
--capabilities tool_use,thinking --reasoning-effort xhigh
```

Prepared runs:

| Client | Run directory |
| --- | --- |
| DSH | `runs/self-hosted-dsh-web-manager-7732758bbb9b` |
| Kimi | `runs/self-hosted-kimi-web-manager-5d497168a1c0` |

## Launch Profiles

A project profile named `qwen38-xhigh` was created in each run's project overlay (`.houmao/agents/launch-profiles/qwen38-xhigh.yaml`). The launcher was extended to accept `--profile` and call `project agents launch --profile` instead of `--specialist`.

DSH profile stores the product-native reasoning default:

```yaml
defaults:
  model:
    name: Qwen/Qwen3.8-27B-FP8
    reasoning:
      level: 3
  posture:
    mode: web
```

Kimi profile stores the model and pins the credential bundle that carries the Kimi env-model thinking inputs:

```yaml
defaults:
  auth: default
  model:
    name: Qwen/Qwen3.8-27B-FP8
  posture:
    mode: web
```

### Why the Env-Model Path Does Not Use `reasoning.level` in the Profile

Houmao deliberately rejects launch-owned reasoning levels for Kimi env-defined models because such models expose no ordered effort catalog (`src/houmao/agents/model_mapping_policy.py`, `_resolve_kimi_reasoning_ladder`). The Kimi auth-variable names (`KIMI_MODEL_CAPABILITIES`, `KIMI_MODEL_THINKING_EFFORT`) also belong to the credential allowlist, so a launch profile `--env-set` cannot override them; the profile's `--auth default` selection pins the bundle that carries the values instead. The effective result is still `xhigh` by default, but the profile field is `auth`, not `reasoning.level`. Making this a first-class profile field for env-defined Kimi models would require a product change.

**Correction (2026-11-24):** This is a limitation of the env-model path, not of Kimi Code. Kimi supports a config-backed model alias with `support_efforts` and `default_effort`, and Houmao already maps numeric levels onto `[thinking] effort` for that path. [R11](2026-11-24-iter3-two-agent-mail-r11-kimi-config-effort.md) replaces this run with a config-backed alias and a visible ordered effort selector.

## Effective Native Verification

DSH materialized patch, `runtime/homes/dsh-brain-20261124-025238Z-8034d9/houmao-profile.patch.json`:

```json
{"id": "llm-pi-ai", "config": {..., "reasoning": "xhigh"}}
```

The prepared native model slot map remains:

```yaml
reasoning_efforts:
  low: low
  medium: medium
  "off": none
  xhigh: xhigh
```

Kimi runtime launch environment, `runtime/homes/kimi-brain-20261124-025244Z-f6beb7/launch.sh`:

```text
export KIMI_MODEL_CAPABILITIES=tool_use,thinking
export KIMI_MODEL_THINKING_EFFORT=xhigh
```

The live `kimi-code` host process environment contains the same values. The native model endpoint reports:

```json
{"provider": "__kimi_env__", "model": "__kimi_env_model__", "display_name": "Qwen/Qwen3.8-27B-FP8", "capabilities": ["tool_use", "thinking"]}
```

The endpoint still advertises no `support_efforts` catalog, so an operator-facing ordered effort selector remains unavailable for the env-defined model even though the forced start effort is `xhigh`. This is the same distinction recorded in R9, now with `thinking` enabled.

## Live R10 Agents

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `bcb2c3da-34eb-4ba5-a608-9def4ae4ad27` | `f5f99863-5e78-478c-967e-28a2fd7d54de` |
| Name | `dsh-mailer-r10` | `kimi-mailer-r10` |
| Address | `dsh-mailer-r10@houmao.localhost` | `kimi-mailer-r10@houmao.localhost` |
| Offline binding | `reg-712dce3df7ea4df08d6e3fa4c2e5fb17` | `reg-526b3c2a199647b19e51db38c010d652` |
| Gateway | `http://127.0.0.1:44977` | `http://127.0.0.1:43047` |
| Native origin | `http://127.0.0.1:46129` | `http://127.0.0.1:45419` |
| Native session | `session-469528f0-aeed-467d-b879-8f756f076135` | `session_9135a3f3-59fc-4369-a248-b6b044e7fac9` |
| Runtime session | `dsh_web-20261124-025238Z-1e7ee677` | `kimi_web-20261124-025245Z-015dc773` |
| Tmux session | `HOUMAO-dsh-mailer-r10-1795488758563` | `HOUMAO-kimi-mailer-r10-1795488765023` |
| Tmux socket | `/tmp/tmux-1001/houmao-fixture-self-hosted-dsh-web-manager-7732758bbb9b` | `/tmp/tmux-1001/houmao-fixture-self-hosted-kimi-web-manager-5d497168a1c0` |

Both states report `availability: available`, `can_accept_prompt_now: true`, `gateway_health: healthy`, `managed_agent_connectivity: connected`, `queue_depth: 0`, and `request_admission: open`. Both gateway roots return HTTP 200 and both `/v1/web/enter` routes return HTTP 302 with fresh session tokens.

Ticketless entrance links:

```text
http://127.0.0.1:44977/v1/web/enter
http://127.0.0.1:43047/v1/web/enter
```

Manifest-based watch and login helpers, all mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r10/attach-dsh-mailer-r10.sh
tmp/houmao-30-iter3-mailbox-r10/attach-kimi-mailer-r10.sh
tmp/houmao-30-iter3-mailbox-r10/login-dsh-mailer-r10.sh
tmp/houmao-30-iter3-mailbox-r10/login-kimi-mailer-r10.sh
```

Both attach helpers passed `--print-target` with the manifest-resolved session name and socket shown above.

## Notifiers and Rule Verification

Both notifiers are enabled at `interval_seconds: 20`, `mode: unread_only`, with `supported: true` and `last_error: null`.

Both live manifests contain all three coordination rules (entrypoint skill first, mail by default, read-only peer inspection). Neither manifest contains `MAIL-OK`.

## Next

Send the first R10 prompt or mail only after the operator confirms. The intended test sequence remains M1 (DSH → Kimi), M2 (Kimi → DSH), then M3 notifier behavior and M4 teardown.
