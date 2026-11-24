# Iteration 3 R11: Kimi Config-Backed Effort Catalog

Date: 2026-11-24. Status: running. This run corrects the R10 conclusion that Kimi could not expose an ordered thinking-effort selector. Kimi Code supports it through `config.toml`; the limitation was the fixture's env-defined model path.

Previous run: [R10 launch-profile xhigh](2026-11-24-iter3-two-agent-mail-r10-launch-profile-xhigh.md).

## Correction

R10 used Kimi's env-defined model (`KIMI_MODEL_NAME` plus `KIMI_MODEL_*` values). That path exposes no ordered effort catalog, so Houmao correctly rejects launch-owned reasoning levels for it. Kimi Code itself does support a config-backed model alias with `support_efforts` and `default_effort`, and Houmao already maps numeric reasoning levels onto that alias's `[thinking] effort`.

Verified against the local Kimi source:

- `extern/orphan/kimi-code/packages/agent-core-v2/src/app/kosongConfig/configSection.ts`: `[models."<alias>"]` accepts `supportEfforts`, `defaultEffort`, `offEffort`, `capabilities`, `provider`, `model`, and `protocol`.
- `extern/orphan/kimi-code/packages/agent-core-v2/docs/config-manifest.toml`: the same fields are documented in snake_case, including `support_efforts` and `default_effort`.
- `extern/orphan/kimi-code/docs/en/configuration/config-files.md`: a complete custom-model example uses `support_efforts = [ "low", "high", "max" ]`, `default_effort = "max"`, and `[thinking] enabled = true, effort = "high"`.
- `src/houmao/agents/model_mapping_policy.py`, `_resolve_kimi_reasoning_ladder`: for a config-backed alias, positive preset `N` maps to the Nth `support_efforts` value and is projected as `[thinking].enabled` plus `[thinking].effort`.

## R10 Teardown

Both R10 notifiers were disabled, both agents were stopped through their agent IDs, and gateway ports `44977` and `43047` were free afterward.

## R11 Material

Root:

```text
tmp/houmao-30-iter3-mailbox-r11/
```

Fresh registry, runtime, mailbox, runs, inputs, and bin. The shared filesystem mailbox was initialized before launch. DSH was prepared as in R10. Kimi was prepared with `--capabilities tool_use,thinking` but without `--reasoning-effort`, because the xhigh value now comes from the config-backed alias.

### Kimi Config-Backed Alias

The credential bundle was rewritten through the adapter-driven writer, not by direct file edits; direct edits are overwritten because the catalog owns the bundle. The update clears every `KIMI_MODEL_*` env binding and attaches `files/config.toml`:

```toml
default_model = "qwen38-xhigh"

[providers.qwen-local]
type = "openai"
base_url = "http://127.0.0.1:14888/v1"
api_key = "local-no-auth"

[models."qwen38-xhigh"]
provider = "qwen-local"
model = "Qwen/Qwen3.8-27B-FP8"
display_name = "Qwen/Qwen3.8-27B-FP8"
protocol = "openai"
max_context_size = 262144
max_output_size = 8192
capabilities = [ "tool_use", "thinking" ]
support_efforts = [ "low", "medium", "high", "xhigh" ]
default_effort = "xhigh"

[thinking]
enabled = true
effort = "xhigh"
```

The same `config.toml` was placed in the Kimi **setup** bundle (`setups/kimi/fixture/config.toml`). This is required because `validate_brain_inputs()` resolves the Kimi reasoning ladder against the setup directory before the runtime home is built. A config in the auth bundle alone is projected too late for that validation. This is a product constraint worth tracking: [issue #94](https://github.com/igamenovoer/houmao/issues/94) proposes resolving from the effective config and using Kimi `config.toml` as the canonical effort source, consistent with Codex.

Campaign helper:

```text
tmp/houmao-30-iter3-mailbox-r11/bin/kimi_config_alias.py
```

### Profile

The Kimi profile `qwen38-xhigh` stores:

```yaml
defaults:
  auth: default
  model:
    name: qwen38-xhigh
    reasoning:
      level: 4
  posture:
    mode: web
```

Level `4` selects the fourth `support_efforts` entry, `xhigh`. The DSH profile remains `reasoning.level: 3`, which selects its `xhigh` slot.

## Effective Native Verification

Kimi runtime `config.toml` contains:

```toml
default_model = "qwen38-xhigh"
...
[models.qwen38-xhigh]
support_efforts = [ "low", "medium", "high", "xhigh" ]
default_effort = "xhigh"

[thinking]
enabled = true
effort = "xhigh"
```

Kimi `/api/v1/config` returns the effective selection:

```json
{
  "default_model": "qwen38-xhigh",
  "models": {
    "qwen38-xhigh": {
      "displayName": "Qwen/Qwen3.8-27B-FP8",
      "capabilities": ["tool_use", "thinking"],
      "supportEfforts": ["low", "medium", "high", "xhigh"],
      "defaultEffort": "xhigh"
    }
  },
  "thinking": {"enabled": true, "effort": "xhigh"}
}
```

Kimi `/api/v1/models` returns the same alias with `support_efforts` and `default_effort`. The web UI therefore has the ordered catalog and the current effort, instead of a disabled selector.

The Kimi launch environment no longer exports `KIMI_MODEL_NAME`, `KIMI_MODEL_CAPABILITIES`, or `KIMI_MODEL_THINKING_EFFORT`. The launch manifest args remain `web --no-open --host 127.0.0.1 --port 0`; the alias is selected by `default_model` in `config.toml`, not by a CLI arg. The Kimi host process environment contains only `KIMI_CODE_HOME` and the non-model engine settings.

DSH materialized patch still contains `"reasoning": "xhigh"` in `llm-pi-ai`.

## Live R11 Agents

| Item | DSH | Kimi |
| --- | --- | --- |
| Agent ID | `3f29cd65-06c0-4b63-8fcf-f8fa13ed556d` | `4724231d-fb56-4d78-a763-fa4a54027536` |
| Name | `dsh-mailer-r11` | `kimi-mailer-r11` |
| Address | `dsh-mailer-r11@houmao.localhost` | `kimi-mailer-r11@houmao.localhost` |
| Offline binding | `reg-a556614de9f743eaaa559ee9eb388eca` | `reg-78bec7acb115440bb5d85c0c0f715b59` |
| Gateway | `http://127.0.0.1:32995` | `http://127.0.0.1:43439` |
| Native origin | `http://127.0.0.1:39909` | `http://127.0.0.1:43373` |
| Native session | `session-b0ac4221-c19e-48c1-8e93-620377430dce` | `session_36bf07ed-e4ea-474c-bab3-594a4cbff298` |
| Runtime session | `dsh_web-20261124-030032Z-8feffad3` | `kimi_web-20261124-030320Z-4fbe722d` |
| Tmux session | `HOUMAO-dsh-mailer-r11-1795489232224` | `HOUMAO-kimi-mailer-r11-1795489400752` |

Both states report `availability: available`, `can_accept_prompt_now: true`, `gateway_health: healthy`, `queue_depth: 0`, and `request_admission: open`. Both gateway roots return HTTP 200 and both `/v1/web/enter` routes return HTTP 302.

Ticketless entrance links:

```text
http://127.0.0.1:32995/v1/web/enter
http://127.0.0.1:43439/v1/web/enter
```

Manifest-based helpers, all mode `0700`:

```text
tmp/houmao-30-iter3-mailbox-r11/attach-dsh-mailer-r11.sh
tmp/houmao-30-iter3-mailbox-r11/attach-kimi-mailer-r11.sh
tmp/houmao-30-iter3-mailbox-r11/login-dsh-mailer-r11.sh
tmp/houmao-30-iter3-mailbox-r11/login-kimi-mailer-r11.sh
```

Both attach helpers passed `--print-target` with the manifest-resolved session and socket.

## Notifiers and Rules

Both notifiers are enabled at `interval_seconds: 20`, `mode: unread_only`, with `supported: true` and no error. Both mailbox bindings are active. Both manifests contain the three coordination rules; neither contains `MAIL-OK`.

## Next

R11 is ready for the M1/M2 mail rounds. The Kimi UI should now show the model as `Qwen/Qwen3.8-27B-FP8` with the ordered effort catalog and `xhigh` selected.
